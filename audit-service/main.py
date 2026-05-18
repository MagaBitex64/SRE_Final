import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Audit Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter("audit_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("audit_request_duration_seconds", "Request latency", ["endpoint"])
AUDIT_COUNT = Gauge("audit_total_logs", "Total audit logs")
AUDIT_CREATED = Counter("audit_created_total", "Total audit logs created", ["action"])

MONGO_URL = os.getenv("MONGO_URL", "mongodb://admin:password@mongodb:27017/")
mongo_client = None
db = None

@app.on_event("startup")
async def startup():
    global mongo_client, db
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client["auditdb"]
    await db["logs"].create_index("created_at")
    count = await db["logs"].count_documents({})
    AUDIT_COUNT.set(count)
    print("MongoDB connected for audit service")

@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()

class AuditIn(BaseModel):
    user_id: Optional[int] = None
    action: str
    service: str
    details: Optional[str] = None
    ip_address: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "audit", "db": "mongodb"}

@app.get("/")
async def get_all():
    start = time.time()
    cursor = db["logs"].find({}, {"_id": 0}).sort("created_at", -1).limit(100)
    rows = await cursor.to_list(length=100)
    REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return rows

@app.get("/user/{user_id}")
async def get_by_user(user_id: int):
    start = time.time()
    cursor = db["logs"].find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    rows = await cursor.to_list(length=100)
    REQUEST_COUNT.labels(method="GET", endpoint="/user", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/user").observe(time.time() - start)
    return rows

@app.get("/service/{service_name}")
async def get_by_service(service_name: str):
    start = time.time()
    cursor = db["logs"].find({"service": service_name}, {"_id": 0}).sort("created_at", -1)
    rows = await cursor.to_list(length=100)
    REQUEST_COUNT.labels(method="GET", endpoint="/service", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/service").observe(time.time() - start)
    return rows

@app.post("/", status_code=201)
async def create(data: AuditIn):
    start = time.time()
    import datetime
    doc = {
        "user_id": data.user_id,
        "action": data.action,
        "service": data.service,
        "details": data.details,
        "ip_address": data.ip_address,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    await db["logs"].insert_one(doc)
    doc.pop("_id", None)
    AUDIT_CREATED.labels(action=data.action).inc()
    AUDIT_COUNT.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/", status="201").inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return doc
