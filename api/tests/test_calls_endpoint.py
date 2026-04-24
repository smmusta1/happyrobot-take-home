"""HTTP-level tests for POST /api/v1/calls/log."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from happyrobot_api.config import get_settings
from happyrobot_api.db import get_db
from happyrobot_api.main import app
from happyrobot_api.models import Call, Offer

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


def _payload(**overrides):
    base = {
        "external_call_id": "hr_abc_123",
        "mc_number": "42",
        "carrier_name": "DEMO CARRIER LLC",
        "load_id": "HR-1001",
        "outcome": "accepted",
        "sentiment": "positive",
        "final_rate": 2400.00,
        "rounds_used": 3,
        "agreement_reached": True,
        "transcript": "hello world",
        "extracted_fields": {"notes": "on-time premium"},
    }
    base.update(overrides)
    return base


def test_log_call_requires_auth(client):
    r = client.post("/api/v1/calls/log", json=_payload())
    assert r.status_code == 401


def test_log_call_happy_path_creates_201(client, db_session):
    r = client.post("/api/v1/calls/log", headers=AUTH, json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == 201
    assert body["call_id"] > 0
    assert body["offers_linked"] == 0

    call = db_session.query(Call).one()
    assert call.external_call_id == "hr_abc_123"
    assert call.outcome == "accepted"
    assert call.sentiment == "positive"
    assert call.final_rate == Decimal("2400.00")
    assert call.extracted_fields == {"notes": "on-time premium"}
    assert call.created_at is not None  # server-side timestamp


def test_log_call_is_idempotent_by_external_id(client, db_session):
    r1 = client.post("/api/v1/calls/log", headers=AUTH, json=_payload())
    assert r1.status_code == 201
    call_id_1 = r1.json()["call_id"]

    # Same external_call_id, different sentiment (e.g., reclassified on retry)
    r2 = client.post(
        "/api/v1/calls/log",
        headers=AUTH,
        json=_payload(sentiment="neutral"),
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == 200
    assert body["call_id"] == call_id_1

    # Still exactly one call row; sentiment was updated
    assert db_session.query(Call).count() == 1
    assert db_session.query(Call).one().sentiment == "neutral"


def test_log_call_links_pre_existing_offers(client, db_session):
    # Simulate offers created during /negotiate before the call webhook fires
    for i, price in enumerate([Decimal("1100.00"), Decimal("1050.00")], start=1):
        db_session.add(
            Offer(
                mc_number="42",
                load_reference_number="HR-1001",
                round_number=i,
                carrier_offer=price,
                agent_counter=price,
                decision="counter",
                notes=None,
            )
        )
    db_session.commit()

    r = client.post("/api/v1/calls/log", headers=AUTH, json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["offers_linked"] == 2

    call_id = body["call_id"]
    linked = db_session.query(Offer).filter(Offer.call_id == call_id).count()
    assert linked == 2


def test_log_call_does_not_link_offers_from_other_carriers(client, db_session):
    db_session.add(
        Offer(
            mc_number="99",  # different MC
            load_reference_number="HR-1001",
            round_number=1,
            carrier_offer=Decimal("1000.00"),
            agent_counter=None,
            decision="pending",
            notes=None,
        )
    )
    db_session.commit()

    r = client.post("/api/v1/calls/log", headers=AUTH, json=_payload())
    assert r.json()["offers_linked"] == 0
    # The unrelated offer stays unlinked
    other = db_session.query(Offer).filter(Offer.mc_number == "99").one()
    assert other.call_id is None


def test_log_call_422_on_invalid_outcome(client):
    r = client.post(
        "/api/v1/calls/log",
        headers=AUTH,
        json=_payload(outcome="something-else"),
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "outcome" in body["error"]


def test_log_call_422_on_invalid_sentiment(client):
    r = client.post(
        "/api/v1/calls/log",
        headers=AUTH,
        json=_payload(sentiment="angry"),
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422


def test_log_call_accepts_declined_outcome_with_no_final_rate(client, db_session):
    r = client.post(
        "/api/v1/calls/log",
        headers=AUTH,
        json=_payload(
            external_call_id="hr_declined_1",
            outcome="declined",
            sentiment="negative",
            final_rate=None,
            agreement_reached=False,
        ),
    )
    assert r.status_code == 201
    call = (
        db_session.query(Call)
        .filter(Call.external_call_id == "hr_declined_1")
        .one()
    )
    assert call.outcome == "declined"
    assert call.final_rate is None
    assert call.agreement_reached is False


def test_log_call_flat_envelope_on_error(client):
    """Calls endpoint uses the flat {status, error} shape, not nested."""
    r = client.post("/api/v1/calls/log", headers=AUTH, json={"outcome": "x", "sentiment": "y"})
    body = r.json()
    assert "statusCode" not in body
    assert "body" not in body
    assert set(body.keys()) == {"status", "error"}
