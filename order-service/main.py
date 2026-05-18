import os
import asyncpg
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Order Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "order_requests_total",
    "Total requests to order service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "order_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)
ORDER_CREATED = Counter(
    "order_created_total",
    "Total orders created"
)
ORDER_STATUS_CHANGES = Counter(
    "order_status_changes_total",
    "Order status changes",
    ["status"]
)
ACTIVE_ORDERS = Gauge(
    "order_active_total",
    "Orders with status pending"
)

DATABASE_URL = os.getenv("ORDER_DATABASE_URL")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price NUMERIC(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status='pending'")
        ACTIVE_ORDERS.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class OrderIn(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    total_price: float

class StatusIn(BaseModel):
    status: str

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "ok", "service": "order"}

@app.get("/")
async def get_all():
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM orders ORDER BY id")
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/{order_id}")
async def get_one(order_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)
    if not row:
        REQUEST_COUNT.labels(method="GET", endpoint="/id", status="404").inc()
        raise HTTPException(404, "Not found")
    REQUEST_COUNT.labels(method="GET", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return dict(row)

@app.post("/", status_code=201)
async def create(data: OrderIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO orders (user_id, product_id, quantity, total_price) VALUES ($1,$2,$3,$4) RETURNING *",
            data.user_id, data.product_id, data.quantity, data.total_price
        )
    ORDER_CREATED.inc()
    ACTIVE_ORDERS.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return dict(row)

@app.patch("/{order_id}/status")
async def update_status(order_id: int, data: StatusIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE orders SET status=$1 WHERE id=$2 RETURNING *",
            data.status, order_id
        )
    if not row:
        REQUEST_COUNT.labels(method="PATCH", endpoint="/status", status="404").inc()
        raise HTTPException(404, "Not found")
    ORDER_STATUS_CHANGES.labels(status=data.status).inc()
    if data.status != "pending":
        ACTIVE_ORDERS.dec()
    REQUEST_COUNT.labels(method="PATCH", endpoint="/status", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/status").observe(time.time() - start)
    return dict(row)

@app.delete("/{order_id}")
async def delete(order_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM orders WHERE id=$1", order_id)
    REQUEST_COUNT.labels(method="DELETE", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return {"deleted": True}