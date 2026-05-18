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

app = FastAPI(title="Review Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "review_requests_total",
    "Total requests to review service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "review_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)
REVIEW_COUNT = Gauge("review_total", "Total reviews")
REVIEW_CREATED = Counter("review_created_total", "Total reviews created")

DATABASE_URL = os.getenv("REVIEW_DATABASE_URL")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5) NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM reviews")
        REVIEW_COUNT.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class ReviewIn(BaseModel):
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "review"}

@app.get("/")
async def get_all():
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM reviews ORDER BY created_at DESC")
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/product/{product_id}")
async def get_by_product(product_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reviews WHERE product_id=$1 ORDER BY created_at DESC",
            product_id
        )
    REQUEST_COUNT.labels(method="GET", endpoint="/product", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/product").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/user/{user_id}")
async def get_by_user(user_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reviews WHERE user_id=$1 ORDER BY created_at DESC",
            user_id
        )
    REQUEST_COUNT.labels(method="GET", endpoint="/user", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/user").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.post("/", status_code=201)
async def create(data: ReviewIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO reviews (user_id, product_id, rating, comment) VALUES ($1,$2,$3,$4) RETURNING *",
            data.user_id, data.product_id, data.rating, data.comment
        )
    REVIEW_CREATED.inc()
    REVIEW_COUNT.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return dict(row)

@app.delete("/{review_id}")
async def delete(review_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM reviews WHERE id=$1", review_id)
    REVIEW_COUNT.dec()
    return {"deleted": True}