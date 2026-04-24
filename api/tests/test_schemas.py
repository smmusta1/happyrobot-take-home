"""Verify our Pydantic schemas round-trip the exact example JSONs from the HappyRobot
Bridge API docs. Any drift between our schemas and the published spec will fail here."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from happyrobot_api.schemas import (
    Carrier,
    CarrierResponse,
    Load,
    LoadResponse,
    LoadsResponse,
    LogOfferRequest,
    LogOfferResponse,
)

# ---------- Canonical examples lifted from docs.happyrobot.ai/bridge-api-reference ----------

CARRIER_EXAMPLE = {
    "statusCode": 200,
    "body": {
        "carrier": {
            "carrier_id": "CAR123456",
            "carrier_name": "ABC Trucking Inc.",
            "status": "active",
            "dot_number": "987654",
            "mc_number": "123456",
            "contacts": [
                {
                    "name": "John Dispatcher",
                    "email": "dispatch@abctrucking.com",
                    "phone": "5551234567",
                    "type": "dispatch",
                    "extension": "101",
                    "preferred_contact_method": "phone",
                }
            ],
            "bridge": {"status": "success", "bridge_carrier_id": "BRK-CAR-789"},
        }
    },
}

LOAD_EXAMPLE = {
    "statusCode": 200,
    "body": {
        "load": {
            "reference_number": "LOAD123",
            "contact": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "15552220123",
                "extension": "123",
                "type": "assigned",
            },
            "type": "owned",
            "stops": [
                {
                    "type": "origin",
                    "location": {
                        "city": "Chicago",
                        "state": "IL",
                        "zip": "60601",
                        "country": "US",
                    },
                    "stop_timestamp_open": "2024-03-20T14:00:00",
                    "stop_timestamp_close": "2024-03-20T16:00:00",
                },
                {
                    "type": "destination",
                    "location": {
                        "city": "New York",
                        "state": "NY",
                        "zip": "10001",
                        "country": "US",
                    },
                    "stop_timestamp_open": "2024-03-21T14:00:00",
                    "stop_timestamp_close": "2024-03-21T16:00:00",
                },
            ],
            "equipment_type": "Dry Van",
            "max_buy": 1500.50,
            "status": "available",
            "is_partial": False,
            "is_hazmat": False,
            "posted_carrier_rate": 1200.00,
            "weight": 40000,
            "number_of_pieces": 100,
            "commodity_type": "Automobile Parts",
            "sale_notes": "This is a test load",
            "dimensions": "53 Feet",
            "branch": "Chicago",
            "miles": 500,
            "bridge": {"status": "success", "bridge_load_id": "BRK-456789"},
        }
    },
}

LOADS_EXAMPLE = {
    "statusCode": 200,
    "body": {
        "loads": [LOAD_EXAMPLE["body"]["load"]],
    },
}


# ---------- Round-trip tests (spec example → Pydantic → dict) ----------


def test_carrier_response_round_trip():
    response = CarrierResponse.model_validate(CARRIER_EXAMPLE)
    assert response.statusCode == 200
    assert response.body.carrier.carrier_name == "ABC Trucking Inc."
    assert response.body.carrier.status == "active"
    assert response.body.carrier.bridge.status == "success"
    assert len(response.body.carrier.contacts) == 1
    assert response.body.carrier.contacts[0].preferred_contact_method == "phone"


def test_load_response_round_trip():
    response = LoadResponse.model_validate(LOAD_EXAMPLE)
    load = response.body.load
    assert load.reference_number == "LOAD123"
    assert load.equipment_type == "Dry Van"
    assert load.posted_carrier_rate == Decimal("1200.00")
    assert load.max_buy == Decimal("1500.50")
    assert load.status == "available"
    assert len(load.stops) == 2
    assert load.stops[0].type == "origin"
    assert load.stops[0].location.city == "Chicago"
    assert load.stops[1].location.state == "NY"


def test_loads_response_round_trip():
    response = LoadsResponse.model_validate(LOADS_EXAMPLE)
    assert len(response.body.loads) == 1
    assert response.body.loads[0].reference_number == "LOAD123"


def test_loads_response_rejects_more_than_three_results():
    """Spec caps at 3 results — schema should enforce."""
    body = {
        "statusCode": 200,
        "body": {"loads": [LOAD_EXAMPLE["body"]["load"]] * 4},
    }
    with pytest.raises(ValidationError):
        LoadsResponse.model_validate(body)


def test_load_rejects_unknown_equipment_type():
    """Strict enum: anything outside the 6 canonical equipment types is rejected."""
    bad = dict(LOAD_EXAMPLE["body"]["load"])
    bad["equipment_type"] = "Tanker"
    with pytest.raises(ValidationError):
        Load.model_validate(bad)


def test_load_rejects_missing_required_fields():
    bad = dict(LOAD_EXAMPLE["body"]["load"])
    del bad["reference_number"]
    with pytest.raises(ValidationError):
        Load.model_validate(bad)


def test_carrier_rejects_unknown_status():
    bad = dict(CARRIER_EXAMPLE["body"]["carrier"])
    bad["status"] = "suspended"  # not in the enum
    with pytest.raises(ValidationError):
        Carrier.model_validate(bad)


# ---------- Offer schemas ----------


def test_log_offer_request_round_trip():
    body = {
        "load_id": "LOAD123456",
        "mc_number": "987654",
        "carrier_offer": 1850.00,
        "notes": "Available for pickup tomorrow morning",
    }
    req = LogOfferRequest.model_validate(body)
    assert req.load_id == "LOAD123456"
    assert req.mc_number == "987654"
    assert req.carrier_offer == Decimal("1850.00")
    assert req.notes == "Available for pickup tomorrow morning"


def test_log_offer_request_notes_optional():
    req = LogOfferRequest.model_validate(
        {"load_id": "L1", "mc_number": "MC1", "carrier_offer": 1500}
    )
    assert req.notes is None


def test_log_offer_request_rejects_missing_fields():
    with pytest.raises(ValidationError):
        LogOfferRequest.model_validate({"load_id": "L1", "mc_number": "MC1"})


def test_log_offer_response_flat_envelope():
    """Unlike other endpoints, log-offer uses a flat {status} envelope per the spec."""
    resp = LogOfferResponse.model_validate({"status": 201})
    assert resp.status == 201
    # Should NOT have a body field
    assert "body" not in resp.model_dump()
