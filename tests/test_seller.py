from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_seller_register_and_login():
    # Generate a unique email for this test run
    random_email = f"test_seller_{uuid.uuid4()}@example.com"
    password = "testpassword"
    name = "Test Seller"

    # 1. Register
    reg_payload = {
        "email": random_email,
        "password": password,
        "name": name
    }
    response = client.post("/seller/register", json=reg_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "seller_id" in data
    seller_id = data["seller_id"]

    # 2. Login
    login_payload = {
        "email": random_email,
        "password": password
    }
    response = client.post("/seller/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["seller_id"] == seller_id
    # assert data["email"] == random_email  # Email is not returned by login endpoint

def test_seller_login_invalid():
    payload = {
        "email": "invalid@example.com",
        "password": "wrong"
    }
    response = client.post("/seller/login", json=payload)
    assert response.status_code == 401
