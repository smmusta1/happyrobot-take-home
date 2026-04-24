"""HTTP-level tests for the dashboard read-side endpoints."""

from datetime import UTC, datetime, timedelta
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


def _make_call(db_session, **overrides) -> Call:
    base = {
        "external_call_id": None,
        "mc_number": "123",
        "carrier_name": "DEMO LLC",
        "load_reference_number": "HR-1001",
        "outcome": "accepted",
        "sentiment": "positive",
        "final_rate": Decimal("2150.00"),
        "rounds_used": 1,
        "agreement_reached": True,
    }
    base.update(overrides)
    call = Call(**base)
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    return call


def test_metrics_summary_requires_auth(client):
    r = client.get("/api/v1/metrics/summary")
    assert r.status_code == 401


def test_metrics_summary_empty_db(client):
    r = client.get("/api/v1/metrics/summary", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["calls_total"] == 0
    assert data["acceptance_rate"] == 0.0
    assert data["avg_rounds_when_accepted"] is None
    assert data["avg_final_rate"] is None
    assert data["outcomes"] == {}
    assert data["sentiment"] == {}
    # calls_by_day always shows 14 entries (for a 14-day rolling chart)
    assert len(data["calls_by_day"]) == 14


def test_metrics_summary_aggregates(client, db_session):
    _make_call(db_session, outcome="accepted", sentiment="positive",
               final_rate=Decimal("2000"), rounds_used=1)
    _make_call(db_session, outcome="accepted", sentiment="positive",
               final_rate=Decimal("2400"), rounds_used=3)
    _make_call(db_session, outcome="declined", sentiment="negative",
               final_rate=None, rounds_used=3, agreement_reached=False)
    _make_call(db_session, outcome="no_match", sentiment="neutral",
               final_rate=None, rounds_used=0, agreement_reached=False)

    r = client.get("/api/v1/metrics/summary", headers=AUTH)
    data = r.json()

    assert data["calls_total"] == 4
    assert data["acceptance_rate"] == 0.5
    assert data["avg_rounds_when_accepted"] == 2.0
    assert Decimal(data["avg_final_rate"]) == Decimal("2200.00")
    assert data["outcomes"] == {"accepted": 2, "declined": 1, "no_match": 1}
    assert data["sentiment"] == {"positive": 2, "negative": 1, "neutral": 1}


def test_list_calls_returns_newest_first(client, db_session):
    c1 = _make_call(db_session, mc_number="100")
    c2 = _make_call(db_session, mc_number="200")
    c3 = _make_call(db_session, mc_number="300")

    r = client.get("/api/v1/calls", headers=AUTH)
    data = r.json()
    assert data["total"] == 3
    ids = [c["id"] for c in data["calls"]]
    assert ids == [c3.id, c2.id, c1.id]


def test_list_calls_pagination(client, db_session):
    for i in range(5):
        _make_call(db_session, mc_number=str(100 + i))
    r = client.get("/api/v1/calls?limit=2&offset=0", headers=AUTH)
    assert len(r.json()["calls"]) == 2
    r = client.get("/api/v1/calls?limit=2&offset=4", headers=AUTH)
    assert len(r.json()["calls"]) == 1
    assert r.json()["total"] == 5


def test_get_call_returns_offers_in_order(client, db_session):
    call = _make_call(db_session)
    for i, price in enumerate([Decimal("2700"), Decimal("2500"), Decimal("2425")], start=1):
        db_session.add(
            Offer(
                call_id=call.id,
                mc_number="123",
                load_reference_number="HR-1001",
                round_number=i,
                carrier_offer=price,
                agent_counter=price,
                decision="counter" if i < 3 else "accept",
                notes=None,
            )
        )
    db_session.commit()

    r = client.get(f"/api/v1/calls/{call.id}", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["call"]["id"] == call.id
    assert len(data["offers"]) == 3
    assert [o["round_number"] for o in data["offers"]] == [1, 2, 3]
    assert data["offers"][-1]["decision"] == "accept"


def test_get_call_404(client):
    r = client.get("/api/v1/calls/999", headers=AUTH)
    assert r.status_code == 404
    assert r.json()["statusCode"] == 404


def test_calls_today_scoped_to_utc_midnight(client, db_session):
    # Create a call timestamped yesterday; should not count in calls_today
    now = datetime.now(UTC).replace(tzinfo=None)
    yesterday = now - timedelta(days=1)
    call = _make_call(db_session)
    call.created_at = yesterday
    db_session.commit()

    r = client.get("/api/v1/metrics/summary", headers=AUTH)
    data = r.json()
    assert data["calls_total"] == 1
    assert data["calls_today"] == 0
