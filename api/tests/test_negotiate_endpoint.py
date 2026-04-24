"""HTTP-level tests for POST /api/v1/negotiate."""

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


def _seed(db_session, load_ref="L1", mc="42", posted="1000.00", max_buy="1200.00"):
    load = Load(
        reference_number=load_ref,
        type="owned",
        status="available",
        equipment_type="Dry Van",
        commodity_type="Freight",
        is_partial=False,
        is_hazmat=False,
        posted_carrier_rate=Decimal(posted),
        max_buy=Decimal(max_buy),
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


def test_negotiate_requires_auth(client):
    r = client.post(
        "/api/v1/negotiate",
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1050},
    )
    assert r.status_code == 401


def test_accept_at_posted_rate(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1000.00},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "accept"
    assert Decimal(body["agent_counter"]) == Decimal("1000.00")
    assert body["round_number"] == 1
    assert body["rounds_remaining"] == 2


def test_counter_round_1(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    body = r.json()
    assert body["decision"] == "counter"
    assert Decimal(body["agent_counter"]) == Decimal("1050.00")
    assert body["round_number"] == 1


def test_counter_uses_prior_agent_counter(client, db_session):
    _seed(db_session)
    # Round 1: carrier 1100 → agent counters 1050
    client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    # Round 2: carrier 1150 → midpoint(1050, 1150) = 1100
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1150.00},
    )
    body = r.json()
    assert body["decision"] == "counter"
    assert Decimal(body["agent_counter"]) == Decimal("1100.00")
    assert body["round_number"] == 2
    assert body["rounds_remaining"] == 1


def test_round_3_accepts_under_max_buy(client, db_session):
    _seed(db_session)
    client.post(
        "/api/v1/negotiate", headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    client.post(
        "/api/v1/negotiate", headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1150.00},
    )
    # Round 3, carrier asks 1180, under max_buy 1200 → accept
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1180.00},
    )
    body = r.json()
    assert body["decision"] == "accept"
    assert body["round_number"] == 3
    assert body["rounds_remaining"] == 0


def test_round_3_declines_over_max_buy(client, db_session):
    _seed(db_session)
    client.post(
        "/api/v1/negotiate", headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    client.post(
        "/api/v1/negotiate", headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1150.00},
    )
    # Round 3, carrier asks 1300 over max_buy 1200 → decline
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1300.00},
    )
    body = r.json()
    assert body["decision"] == "decline"
    assert body["agent_counter"] is None


def test_idempotent_on_duplicate_offer(client, db_session):
    _seed(db_session)
    payload = {"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00}
    r1 = client.post("/api/v1/negotiate", headers=AUTH, json=payload)
    r2 = client.post("/api/v1/negotiate", headers=AUTH, json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Same decision, same round — no new row
    assert r1.json()["decision"] == r2.json()["decision"]
    assert r1.json()["round_number"] == r2.json()["round_number"]
    assert db_session.query(Offer).count() == 1


def test_404_when_load_missing(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "NOPE", "mc_number": "42", "carrier_offer": 1100.00},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["statusCode"] == 404
    assert "NOPE" in body["body"]["error"]


def test_404_when_carrier_missing(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "9999", "carrier_offer": 1100.00},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["statusCode"] == 404
    assert "9999" in body["body"]["error"]


def test_400_on_non_positive_offer(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 0},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["statusCode"] == 400
    assert "greater than zero" in body["body"]["error"]


def test_offers_linked_to_completed_call_do_not_count(client, db_session):
    """Offers already tied to a completed Call (via call_id) should not
    inflate the round counter — the call is over, next negotiation is a new session.
    """
    _seed(db_session)
    # Simulate 2 prior offers from a completed call (call_id is set)
    for i, price in enumerate([Decimal("1100"), Decimal("1125")], start=1):
        db_session.add(
            Offer(
                mc_number="42",
                load_reference_number="L1",
                round_number=i,
                carrier_offer=price,
                agent_counter=price,
                decision="counter",
                notes=None,
                call_id=999,  # already linked to a completed call
            )
        )
    db_session.commit()

    # A new negotiation starts — should be round 1 despite the prior offers
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    body = r.json()
    assert body["round_number"] == 1
    assert body["rounds_remaining"] == 2


def test_stale_offers_do_not_count_toward_round(client, db_session):
    """Offers older than ROUND_RESET_WINDOW (30 min) should not inflate the round counter.

    Ensures that an evaluator testing the demo a day later starts at round 1, not
    round N+1 inheriting our dev-time test offers.
    """
    _seed(db_session)
    # Simulate 3 prior offers from a previous session (31 min ago)
    stale_time = datetime(2026, 4, 22, 12, 0, 0)  # far in the past
    for i, price in enumerate([Decimal("1100"), Decimal("1125"), Decimal("1150")], start=1):
        offer = Offer(
            mc_number="42",
            load_reference_number="L1",
            round_number=i,
            carrier_offer=price,
            agent_counter=price,
            decision="counter",
            notes=None,
        )
        db_session.add(offer)
        db_session.flush()
        # Backdate the row
        offer.created_at = stale_time
    db_session.commit()

    # Now a fresh offer — should be treated as round 1, not round 4
    r = client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["round_number"] == 1
    assert body["rounds_remaining"] == 2


def test_persists_offer_with_decision_and_counter(client, db_session):
    _seed(db_session)
    client.post(
        "/api/v1/negotiate",
        headers=AUTH,
        json={"load_id": "L1", "mc_number": "42", "carrier_offer": 1100.00},
    )
    offer = db_session.query(Offer).one()
    assert offer.decision == "counter"
    assert offer.agent_counter == Decimal("1050.00")
    assert offer.round_number == 1
