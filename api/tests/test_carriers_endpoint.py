"""HTTP-level tests for GET /api/v1/carriers/find — mocks FMCSA, exercises the real router."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from happyrobot_api.config import get_settings
from happyrobot_api.db import get_db
from happyrobot_api.main import app

VALID_KEY = "test-key"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("API_KEY", VALID_KEY)
    monkeypatch.setenv("FMCSA_WEB_KEY", "fake")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


AUTH = {"Authorization": f"Bearer {VALID_KEY}"}


def test_find_carrier_returns_bridge_envelope(client):
    fake = {
        "legalName": "TEST CARRIER",
        "dotNumber": 555,
        "allowedToOperate": "Y",
        "statusCode": "A",
    }
    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=fake):
        r = client.get("/api/v1/carriers/find?mc=42", headers=AUTH)

    assert r.status_code == 200
    body = r.json()
    assert body["statusCode"] == 200
    assert body["body"]["carrier"]["carrier_name"] == "TEST CARRIER"
    assert body["body"]["carrier"]["status"] == "active"
    assert body["body"]["carrier"]["mc_number"] == "42"


def test_find_carrier_404_when_fmcsa_empty(client):
    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=None):
        r = client.get("/api/v1/carriers/find?mc=99999999", headers=AUTH)
    assert r.status_code == 404


def test_find_carrier_400_when_no_mc_or_dot(client):
    r = client.get("/api/v1/carriers/find", headers=AUTH)
    assert r.status_code == 400
    body = r.json()
    assert body["statusCode"] == 400
    assert "mc or dot" in body["body"]["error"]


def test_find_carrier_404_returns_bridge_envelope(client):
    from unittest.mock import patch

    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=None):
        r = client.get("/api/v1/carriers/find?mc=99999999", headers=AUTH)
    assert r.status_code == 404
    body = r.json()
    assert body["statusCode"] == 404
    assert "Carrier not found" in body["body"]["error"]


def test_find_carrier_requires_auth(client):
    r = client.get("/api/v1/carriers/find?mc=42")
    assert r.status_code == 401
