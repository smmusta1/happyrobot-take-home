import pytest
from fastapi.testclient import TestClient

from happyrobot_api.config import get_settings
from happyrobot_api.main import app

VALID_KEY = "test-key-abc123"


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", VALID_KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


client = TestClient(app)


def test_health_is_public():
    """Health endpoint must work without any auth — Railway needs this for liveness probes."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_rejects_missing_header():
    response = client.get("/api/v1/ping")
    assert response.status_code == 401
    body = response.json()
    assert body["statusCode"] == 401
    assert "Missing" in body["body"]["error"]


def test_protected_route_rejects_wrong_key():
    response = client.get("/api/v1/ping", headers={"Authorization": "Bearer wrong-key"})
    assert response.status_code == 401
    body = response.json()
    assert body["statusCode"] == 401
    assert body["body"]["error"] == "Invalid API key"


def test_protected_route_rejects_non_bearer_scheme():
    # Basic auth instead of Bearer → should be rejected.
    response = client.get("/api/v1/ping", headers={"Authorization": "Basic dGVzdDp0ZXN0"})
    assert response.status_code == 401


def test_protected_route_accepts_valid_key():
    response = client.get("/api/v1/ping", headers={"Authorization": f"Bearer {VALID_KEY}"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_server_key_rejects_everything():
    """Safety net: if API_KEY env var is unset, no request should authenticate."""
    import os

    os.environ["API_KEY"] = ""
    get_settings.cache_clear()
    response = client.get("/api/v1/ping", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 401
