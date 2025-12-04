
from app.core.config import settings


def test_admin_login_success(client):
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

def test_admin_login_failure(client):
    payload = {
        "email": "wrong@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/admin/login", json=payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin credentials"}
