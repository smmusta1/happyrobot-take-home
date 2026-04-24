"""HTTP-level tests for POST /api/v1/offers/log."""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from happyrobot_api.config import get_settings
from happyrobot_api.db import get_db
from happyrobot_api.main import app
from happyrobot_api.models import Carrier, Load, Offer

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


def _seed(db_session, load_ref="L1", mc="42"):
    load = Load(
        reference_number=load_ref,
        type="owned",
        status="available",
        equipment_type="Dry Van",
        commodity_type="Freight",
        is_partial=False,
        is_hazmat=False,
        posted_carrier_rate=Decimal("1000.00"),
        max_buy=Decimal("1200.00"),
        origin_city="Chicago",
        origin_state="IL",
        origin_zip="60601",
        origin_country="US",
        origin_open=datetime(2026, 5, 1, 8, 0),
        origin_close=datetime(2026, 5, 1, 18, 0),
        destination_city="Dallas",
        destination_state="TX",
        destination_zip="75201",
        destination_country="US",
        destination_open=datetime(2026, 5, 2, 8, 0),
        destination_close=datetime(2026, 5, 2, 18, 0),
    )
    carrier = Carrier(
        mc_number=mc,
        dot_number="9999",
        carrier_name="TEST CARRIER",
        status="active",
        allowed_to_operate=True,
    )
    db_session.add_all([load, carrier])
    db_session.commit()


def test_log_offer_requires_auth(client):
    r = client.post(
        "/api/v1/offers/log",
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100},
    )
    assert r.status_code == 401


def test_log_offer_success_returns_flat_201_envelope(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.0, "notes": "first try"},
    )
    assert r.status_code == 201
    assert r.json() == {"status": 201}

    offer = db_session.query(Offer).one()
    assert offer.mc_number == "42"
    assert offer.load_reference_number == "L1"
    assert offer.carrier_offer == Decimal("1100.00")
    assert offer.round_number == 1
    assert offer.decision == "pending"
    assert offer.notes == "first try"


def test_log_offer_increments_round_number(client, db_session):
    _seed(db_session)
    for i, price in enumerate([1050, 1075, 1100], start=1):
        r = client.post(
            "/api/v1/offers/log",
            headers=AUTH,
            json={"load_id": "L1", "mc_number": "42", "carrier_offer": price},
        )
        assert r.status_code == 201
        last = db_session.query(Offer).order_by(Offer.id.desc()).first()
        assert last.round_number == i


def test_log_offer_404_when_load_missing(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"load_id": "NOPE", "mc_number": "42", "carrier_offer": 1100.0},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "NOPE" in body["error"]


def test_log_offer_404_when_carrier_missing(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "9999", "carrier_offer": 1100.0},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "9999" in body["error"]


def test_log_offer_409_on_duplicate(client, db_session):
    _seed(db_session)
    payload = {"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.0}
    r1 = client.post("/api/v1/offers/log", headers=AUTH, json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/offers/log", headers=AUTH, json=payload)
    assert r2.status_code == 409
    body = r2.json()
    assert body["status"] == 409
    assert "identical" in body["error"].lower()


def test_log_offer_400_on_non_positive_offer(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 0},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["status"] == 400
    assert "greater than zero" in body["error"]


def test_log_offer_422_on_missing_field(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"mc_number": "42", "carrier_offer": 1100.0},  # missing load_id
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "load_id" in body["error"]


def test_log_offer_flat_envelope_not_nested(client, db_session):
    """Offers spec uses {status, error}, not {statusCode, body:{error}}."""
    _seed(db_session)
    r = client.post(
        "/api/v1/offers/log",
        headers=AUTH,
        json={"load_id": "NOPE", "mc_number": "42", "carrier_offer": 100},
    )
    body = r.json()
    assert "statusCode" not in body
    assert "body" not in body
    assert set(body.keys()) == {"status", "error"}
