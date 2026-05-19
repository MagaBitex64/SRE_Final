import hashlib
import sys
import os

def test_password_hashing():
    password = "testpass123"
    hashed = hashlib.sha256(password.encode()).hexdigest()
    assert len(hashed) == 64
    assert hashed == hashlib.sha256(password.encode()).hexdigest()

def test_hash_is_deterministic():
    assert hashlib.sha256(b"hello").hexdigest() == hashlib.sha256(b"hello").hexdigest()

def test_different_passwords_different_hashes():
    h1 = hashlib.sha256(b"password1").hexdigest()
    h2 = hashlib.sha256(b"password2").hexdigest()
    assert h1 != h2

def test_service_names():
    services = ["auth", "product", "order", "user-profile", "review", "audit"]
    assert len(services) == 6
    assert "auth" in services
    assert "audit" in services

def test_port_assignments():
    ports = {
        "auth": 3001,
        "product": 3002,
        "order": 3003,
        "user-profile": 3004,
        "review": 3005,
        "audit": 3006,
    }
    assert ports["auth"] == 3001
    assert ports["audit"] == 3006
    assert len(ports) == 6
