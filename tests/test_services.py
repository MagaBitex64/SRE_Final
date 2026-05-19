import pytest
import requests
import random

def test_auth_health():
    r = requests.get("http://localhost:3001/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_product_health():
    r = requests.get("http://localhost:3002/health")
    assert r.status_code == 200

def test_order_health():
    r = requests.get("http://localhost:3003/health")
    assert r.status_code == 200

def test_user_health():
    r = requests.get("http://localhost:3004/health")
    assert r.status_code == 200

def test_review_health():
    r = requests.get("http://localhost:3005/health")
    assert r.status_code == 200

def test_audit_health():
    r = requests.get("http://localhost:3006/health")
    assert r.status_code == 200

def test_get_products():
    r = requests.get("http://localhost:3002/products")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_audit_logs():
    r = requests.get("http://localhost:3006/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_register_and_login():
    username = f"testuser_{random.randint(100000, 999999)}"
    reg = requests.post("http://localhost:3001/register", json={
        "username": username,
        "password": "testpass123"
    })
    assert reg.status_code in [200, 201]

    login = requests.post("http://localhost:3001/login", json={
        "username": username,
        "password": "testpass123"
    })
    assert login.status_code == 200
    assert "token" in login.json()