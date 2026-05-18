import os
import asyncpg
import hashlib
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Auth Service")
Instrumentator().instrument(app).expose(app)

REQUEST_COUNT = Counter(
    "auth_requests_total",
    "Total requests to auth service",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "auth_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"]
)
ACTIVE_USERS = Gauge(
    "auth_active_users_total",
    "Total registered users in DB"
)
LOGIN_SUCCESS = Counter(
    "auth_login_success_total",
    "Successful logins"
)
LOGIN_FAILURE = Counter(
    "auth_login_failure_total",
    "Failed login attempts"
)
REGISTER_COUNT = Counter(
    "auth_register_total",
    "Total registrations"
)

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("AUTH_DATABASE_URL")
pool = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        ACTIVE_USERS.set(count)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

class UserIn(BaseModel):
    username: str
    password: str

class TokenIn(BaseModel):
    token: str

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "ok", "service": "auth"}

@app.post("/register", status_code=201)
async def register(data: UserIn):
    start = time.time()
    hashed = hash_password(data.password)
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users (username, password) VALUES ($1, $2) RETURNING id, username",
                data.username, hashed
            )
        REGISTER_COUNT.inc()
        ACTIVE_USERS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/register", status="201").inc()
        REQUEST_LATENCY.labels(endpoint="/register").observe(time.time() - start)
        return dict(row)
    except Exception as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/register", status="400").inc()
        raise HTTPException(400, str(e))

@app.post("/login")
async def login(data: UserIn):
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE username=$1", data.username)
    if not row or not verify_password(data.password, row["password"]):
        LOGIN_FAILURE.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/login", status="401").inc()
        raise HTTPException(401, "Invalid credentials")
    expire = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode(
        {"sub": str(row["id"]), "username": row["username"], "exp": expire},
        SECRET_KEY, algorithm="HS256"
    )
    LOGIN_SUCCESS.inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/login", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/login").observe(time.time() - start)
    return {"token": token}

@app.post("/verify")
async def verify(data: TokenIn):
    start = time.time()
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=["HS256"])
        REQUEST_COUNT.labels(method="POST", endpoint="/verify", status="200").inc()
        REQUEST_LATENCY.labels(endpoint="/verify").observe(time.time() - start)
        return {"valid": True, "user": payload}
    except JWTError:
        REQUEST_COUNT.labels(method="POST", endpoint="/verify", status="401").inc()
        raise HTTPException(401, "Invalid token")