"""HTTP-level tests for GET /api/v1/loads and /api/v1/loads/{reference_number}."""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from happyrobot_api.config import get_settings
from happyrobot_api.db import get_db
from happyrobot_api.main import app
from happyrobot_api.models import Load

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


def _make_load(
    db_session,
    ref: str,
    origin_city="Chicago",
    origin_state="IL",
    destination_city="Dallas",
    destination_state="TX",
    equipment_type="Dry Van",
    status="available",
    origin_open=datetime(2026, 5, 1, 8, 0),
    origin_close=datetime(2026, 5, 1, 18, 0),
) -> Load:
    load = Load(
        reference_number=ref,
        type="owned",
        status=status,
        equipment_type=equipment_type,
        commodity_type="General Freight",
        is_partial=False,
        is_hazmat=False,
        posted_carrier_rate=Decimal("1200.00"),
        max_buy=Decimal("1400.00"),
        origin_city=origin_city,
        origin_state=origin_state,
        origin_zip="60601",
        origin_country="US",
        origin_open=origin_open,
        origin_close=origin_close,
        destination_city=destination_city,
        destination_state=destination_state,
        destination_zip="75201",
        destination_country="US",
        destination_open=origin_open,
        destination_close=origin_close,
    )
    db_session.add(load)
    db_session.commit()
    return load


def test_search_requires_auth(client):
    r = client.get("/api/v1/loads")
    assert r.status_code == 401


def test_search_returns_bridge_envelope(client, db_session):
    _make_load(db_session, "L1")
    r = client.get("/api/v1/loads", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["statusCode"] == 200
    assert len(body["body"]["loads"]) == 1
    load = body["body"]["loads"][0]
    assert load["reference_number"] == "L1"
    assert len(load["stops"]) == 2
    assert load["stops"][0]["type"] == "origin"
    assert load["stops"][0]["location"]["city"] == "Chicago"
    assert load["stops"][1]["type"] == "destination"


def test_search_caps_at_three(client, db_session):
    for i in range(5):
        _make_load(db_session, f"L{i}")
    r = client.get("/api/v1/loads", headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()["body"]["loads"]) == 3


def test_search_filters_by_origin_state(client, db_session):
    _make_load(db_session, "LA", origin_state="IL")
    _make_load(db_session, "LB", origin_state="CA")
    r = client.get("/api/v1/loads?origin_state=CA", headers=AUTH)
    refs = [load["reference_number"] for load in r.json()["body"]["loads"]]
    assert refs == ["LB"]


def test_search_filters_by_equipment_type(client, db_session):
    _make_load(db_session, "DV", equipment_type="Dry Van")
    _make_load(db_session, "RF", equipment_type="Reefer")
    r = client.get("/api/v1/loads?equipment_type=Reefer", headers=AUTH)
    refs = [load["reference_number"] for load in r.json()["body"]["loads"]]
    assert refs == ["RF"]


def test_search_excludes_non_available(client, db_session):
    _make_load(db_session, "LIVE", status="available")
    _make_load(db_session, "TAKEN", status="covered")
    r = client.get("/api/v1/loads", headers=AUTH)
    refs = [load["reference_number"] for load in r.json()["body"]["loads"]]
    assert refs == ["LIVE"]


def test_search_filters_by_pickup_date(client, db_session):
    _make_load(
        db_session,
        "MAY1",
        origin_open=datetime(2026, 5, 1, 8, 0),
        origin_close=datetime(2026, 5, 1, 18, 0),
    )
    _make_load(
        db_session,
        "MAY2",
        origin_open=datetime(2026, 5, 2, 8, 0),
        origin_close=datetime(2026, 5, 2, 18, 0),
    )
    r = client.get("/api/v1/loads?pickup_date=2026-05-02", headers=AUTH)
    refs = [load["reference_number"] for load in r.json()["body"]["loads"]]
    assert refs == ["MAY2"]


def test_search_case_insensitive_city(client, db_session):
    _make_load(db_session, "CHI", origin_city="Chicago")
    r = client.get("/api/v1/loads?origin_city=CHICAGO", headers=AUTH)
    assert [load["reference_number"] for load in r.json()["body"]["loads"]] == ["CHI"]


def test_search_accepts_but_ignores_geo_filters(client, db_session):
    _make_load(db_session, "ANY")
    r = client.get(
        "/api/v1/loads?origin_lat=41.8&origin_lng=-87.6&origin_radius=50", headers=AUTH
    )
    assert r.status_code == 200
    assert len(r.json()["body"]["loads"]) == 1


def test_get_load_by_reference_number(client, db_session):
    _make_load(db_session, "L42")
    r = client.get("/api/v1/loads/L42", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["statusCode"] == 200
    assert body["body"]["load"]["reference_number"] == "L42"


def test_get_load_404_returns_bridge_envelope(client):
    r = client.get("/api/v1/loads/NOPE", headers=AUTH)
    assert r.status_code == 404
    body = r.json()
    assert body["statusCode"] == 404
    assert "not found" in body["body"]["error"].lower()


def test_get_load_requires_auth(client):
    r = client.get("/api/v1/loads/L1")
    assert r.status_code == 401
