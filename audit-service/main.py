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

app = FastAPI(title="Audit Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "audit_requests_total",
    "Total requests to audit service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "audit_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)
AUDIT_COUNT = Gauge("audit_total_logs", "Total audit logs")
AUDIT_CREATED = Counter("audit_created_total", "Total audit logs created", ["action"])

DATABASE_URL = os.getenv("AUDIT_DATABASE_URL")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                action VARCHAR(100) NOT NULL,
                service VARCHAR(100) NOT NULL,
                details TEXT,
                ip_address VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM audit_logs")
        AUDIT_COUNT.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class AuditIn(BaseModel):
    user_id: Optional[int] = None
    action: str
    service: str
    details: Optional[str] = None
    ip_address: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "audit"}

@app.get("/")
async def get_all():
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100")
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/user/{user_id}")
async def get_by_user(user_id: int):
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_logs WHERE user_id=$1 ORDER BY created_at DESC",
            user_id
        )
    REQUEST_COUNT.labels(method="GET", endpoint="/user", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/user").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.get("/service/{service_name}")
async def get_by_service(service_name: str):
    start = time.time()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_logs WHERE service=$1 ORDER BY created_at DESC",
            service_name
        )
    REQUEST_COUNT.labels(method="GET", endpoint="/service", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/service").observe(time.time() - start)
    return [dict(r) for r in rows]

@app.post("/", status_code=201)
async def create(data: AuditIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO audit_logs (user_id, action, service, details, ip_address) VALUES ($1,$2,$3,$4,$5) RETURNING *",
            data.user_id, data.action, data.service, data.details, data.ip_address
        )
    AUDIT_CREATED.labels(action=data.action).inc()
    AUDIT_COUNT.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return dict(row)