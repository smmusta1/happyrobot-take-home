"""Unit tests for FMCSA eligibility mapping and cache behavior (no network)."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from happyrobot_api.config import Settings
from happyrobot_api.fmcsa import _map_eligibility, lookup_carrier
from happyrobot_api.models import Carrier


def _settings() -> Settings:
    return Settings(api_key="k", fmcsa_web_key="web", fmcsa_cache_hours=24)


@pytest.mark.parametrize(
    "allowed,status_code,expected",
    [
        ("Y", "A", "active"),
        ("Y", "I", "inactive"),
        ("Y", None, "inactive"),
        ("N", "A", "fail"),
        ("N", "I", "fail"),
        (None, None, "not_set"),
    ],
)
def test_eligibility_mapping(allowed, status_code, expected):
    assert _map_eligibility({"allowedToOperate": allowed, "statusCode": status_code}) == expected


def test_lookup_fetches_from_fmcsa_when_cache_empty(db_session):
    fake_payload = {
        "legalName": "TEST CARRIER LLC",
        "dotNumber": 123456,
        "allowedToOperate": "Y",
        "statusCode": "A",
    }
    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=fake_payload) as mock_fetch:
        result = lookup_carrier(db_session, _settings(), "TEST1")

    assert mock_fetch.called
    assert result is not None
    assert result.carrier_name == "TEST CARRIER LLC"
    assert result.status == "active"
    assert result.mc_number == "TEST1"

    cached = db_session.query(Carrier).filter_by(mc_number="TEST1").one()
    assert cached.carrier_name == "TEST CARRIER LLC"
    assert cached.fmcsa_raw == fake_payload


def test_lookup_returns_none_when_fmcsa_has_no_record(db_session):
    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=None):
        result = lookup_carrier(db_session, _settings(), "NOTREAL")
    assert result is None
    assert db_session.query(Carrier).count() == 0


def test_lookup_uses_cache_within_ttl_without_hitting_fmcsa(db_session):
    db_session.add(
        Carrier(
            mc_number="CACHED",
            dot_number="999",
            carrier_name="CACHED CARRIER",
            status="active",
            allowed_to_operate=True,
            fmcsa_raw={"legalName": "CACHED CARRIER"},
            cached_at=datetime.now() - timedelta(hours=1),
        )
    )
    db_session.commit()

    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier") as mock_fetch:
        result = lookup_carrier(db_session, _settings(), "CACHED")

    assert not mock_fetch.called  # cache hit — no network
    assert result is not None
    assert result.carrier_name == "CACHED CARRIER"


def test_lookup_refetches_when_cache_stale(db_session):
    db_session.add(
        Carrier(
            mc_number="STALE",
            dot_number="111",
            carrier_name="OLD NAME",
            status="inactive",
            allowed_to_operate=True,
            fmcsa_raw={"legalName": "OLD NAME"},
            cached_at=datetime.now() - timedelta(hours=48),  # older than 24h TTL
        )
    )
    db_session.commit()

    fresh = {
        "legalName": "NEW NAME",
        "dotNumber": 111,
        "allowedToOperate": "Y",
        "statusCode": "A",
    }
    with patch("happyrobot_api.fmcsa.fetch_fmcsa_carrier", return_value=fresh) as mock_fetch:
        result = lookup_carrier(db_session, _settings(), "STALE")

    assert mock_fetch.called
    assert result is not None
    assert result.carrier_name == "NEW NAME"
    assert result.status == "active"

    cached = db_session.query(Carrier).filter_by(mc_number="STALE").one()
    assert cached.carrier_name == "NEW NAME"
