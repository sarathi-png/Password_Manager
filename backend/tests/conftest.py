import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.mkdtemp(prefix="vault-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MASTER_KEY_FILE"] = str(Path(_tmp) / "master.key")
os.environ["JWT_SECRET"] = "test-secret-0123456789-0123456789-0123456789"
os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
os.environ["INITIAL_ADMIN_PASSWORD"] = "adminpass123"
os.environ["RATE_LIMIT_LOGIN_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_API_PER_MINUTE"] = "10000"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def employee_token(client, admin_headers):
    resp = client.post(
        "/api/users",
        json={"username": "employee1", "password": "employeepass1", "role": "employee"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/auth/login", json={"username": "employee1", "password": "employeepass1"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def employee_headers(employee_token):
    return {"Authorization": f"Bearer {employee_token}"}


@pytest.fixture(scope="session")
def sample_entry(client, admin_headers):
    resp = client.post(
        "/api/entries",
        json={
            "title": "Gmail",
            "url": "https://mail.google.com",
            "username": "user@example.com",
            "password": "s3cret-Ä",
            "notes": "primary inbox",
            "category": "email",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()