from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_admin_login_success():
    payload = {
        "email": settings.ADMIN_EMAIL,
        "password": settings.ADMIN_PASSWORD
    }
    response = client.post("/admin/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["email"] == settings.ADMIN_EMAIL
    assert "admin_id" in data

def test_admin_login_failure():
    payload = {
        "email": "wrong@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/admin/login", json=payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin credentials"}
