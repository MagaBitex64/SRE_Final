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

app = FastAPI(title="User Profile Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "userprofile_requests_total",
    "Total requests to user profile service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "userprofile_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)
PROFILE_COUNT = Gauge(
    "userprofile_total",
    "Total user profiles"
)
PROFILE_CREATED = Counter(
    "userprofile_created_total",
    "Total profiles created"
)
PROFILE_UPDATED = Counter(
    "userprofile_updated_total",
    "Total profiles updated"
)

DATABASE_URL = os.getenv("USER_DATABASE_URL")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                full_name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM profiles")
        PROFILE_COUNT.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class ProfileIn(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "ok", "service": "user-profile"}

@app.get("/")
async def get_all():
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM profiles ORDER BY id")
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/{user_id}")
async def get_one(user_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM profiles WHERE user_id=$1", user_id)
    if not row:
        REQUEST_COUNT.labels(method="GET", endpoint="/id", status="404").inc()
        raise HTTPException(404, "Not found")
    REQUEST_COUNT.labels(method="GET", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return dict(row)

@app.post("/", status_code=201)
async def create(data: ProfileIn):
    start = time.time()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO profiles (user_id, full_name, email, phone, avatar_url) VALUES ($1,$2,$3,$4,$5) RETURNING *",
                data.user_id, data.full_name, data.email, data.phone, data.avatar_url
            )
        PROFILE_CREATED.inc()
        PROFILE_COUNT.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
        REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
        return dict(row)
    except Exception as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/", status="400").inc()
        raise HTTPException(400, str(e))

@app.put("/{user_id}")
async def update(user_id: int, data: ProfileIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE profiles SET full_name=$1, email=$2, phone=$3, avatar_url=$4, updated_at=NOW() WHERE user_id=$5 RETURNING *",
            data.full_name, data.email, data.phone, data.avatar_url, user_id
        )
    if not row:
        REQUEST_COUNT.labels(method="PUT", endpoint="/id", status="404").inc()
        raise HTTPException(404, "Not found")
    PROFILE_UPDATED.inc()
    REQUEST_COUNT.labels(method="PUT", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return dict(row)

@app.delete("/{user_id}")
async def delete(user_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM profiles WHERE user_id=$1", user_id)
    PROFILE_COUNT.dec()
    REQUEST_COUNT.labels(method="DELETE", endpoint="/id", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/id").observe(time.time() - start)
    return {"deleted": True}