import pytest
import requests

BASE = "http://localhost"

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

def test_register():
    import random
    r = requests.post("http://localhost:3001/register", json={
        "username": f"testuser_{random.randint(1000,9999)}",
        "password": "testpass123"
    })
    assert r.status_code in [200, 201]

def test_audit_create():
    r = requests.post("http://localhost:3006/", json={
        "action": "test",
        "service": "test-service",
        "details": "automated test"
    })
    assert r.status_code == 201

def test_audit_get():
    r = requests.get("http://localhost:3006/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
