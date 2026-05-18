import os
import asyncpg
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Product Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "product_requests_total",
    "Total requests to product service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "product_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)
PRODUCT_COUNT = Gauge(
    "product_total_items",
    "Total products in catalog"
)
PRODUCT_CREATED = Counter(
    "product_created_total",
    "Total products created"
)
PRODUCT_DELETED = Counter(
    "product_deleted_total",
    "Total products deleted"
)

DATABASE_URL = os.getenv("PRODUCT_DATABASE_URL")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price NUMERIC(10,2) NOT NULL,
                stock INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        PRODUCT_COUNT.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class ProductIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "ok", "service": "product"}

@app.get("/")
async def get_all():
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM products ORDER BY id")
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/{product_id}")
async def get_one(product_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM products WHERE id=$1", product_id)
    if not row:
        REQUEST_COUNT.labels(method="GET", endpoint="/id", status="404").inc()
        raise HTTPException(404, "Not found")
    REQUEST_COUNT.labels(method="GET", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return dict(row)

@app.post("/", status_code=201)
async def create(data: ProductIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO products (name, description, price, stock) VALUES ($1,$2,$3,$4) RETURNING *",
            data.name, data.description, data.price, data.stock
        )
    PRODUCT_CREATED.inc()
    PRODUCT_COUNT.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return dict(row)

@app.put("/{product_id}")
async def update(product_id: int, data: ProductIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE products SET name=$1, description=$2, price=$3, stock=$4 WHERE id=$5 RETURNING *",
            data.name, data.description, data.price, data.stock, product_id
        )
    if not row:
        REQUEST_COUNT.labels(method="PUT", endpoint="/id", status="404").inc()
        raise HTTPException(404, "Not found")
    REQUEST_COUNT.labels(method="PUT", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return dict(row)

@app.delete("/{product_id}")
async def delete(product_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM products WHERE id=$1", product_id)
    PRODUCT_DELETED.inc()
    PRODUCT_COUNT.dec()
    REQUEST_COUNT.labels(method="DELETE", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return {"deleted": True}