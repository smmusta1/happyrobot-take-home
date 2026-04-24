"""Live integration tests against the real FMCSA QCMobile API.

Skipped when FMCSA_WEB_KEY is not set in the environment. This is so CI can
still run unit tests without needing the key.
"""

import os

import pytest

from happyrobot_api.config import Settings
from happyrobot_api.fmcsa import fetch_fmcsa_carrier, lookup_carrier

pytestmark = pytest.mark.skipif(
    not os.getenv("FMCSA_WEB_KEY"),
    reason="FMCSA_WEB_KEY not set — skipping live FMCSA tests",
)


def _settings() -> Settings:
    return Settings(
        api_key="k",
        fmcsa_web_key=os.environ["FMCSA_WEB_KEY"],
        fmcsa_cache_hours=24,
    )


def test_fetch_active_carrier():
    """MC 123 (GREENLIGHT TRANS LLC) — confirmed active in FMCSA."""
    raw = fetch_fmcsa_carrier(_settings(), "123")
    assert raw is not None
    assert raw["allowedToOperate"] == "Y"
    assert raw["statusCode"] == "A"


def test_fetch_inactive_carrier():
    """MC 44110 (BNR ENTERPRISES INC) — active in FMCSA's records but statusCode I."""
    raw = fetch_fmcsa_carrier(_settings(), "44110")
    assert raw is not None
    assert raw["statusCode"] == "I"


def test_fetch_nonexistent_carrier_returns_none():
    raw = fetch_fmcsa_carrier(_settings(), "99999999")
    assert raw is None


def test_lookup_carrier_end_to_end_active(db_session):
    """End-to-end: live FMCSA call for an active carrier, cached, Bridge-schema response."""
    result = lookup_carrier(db_session, _settings(), "123")
    assert result is not None
    assert result.status == "active"
    assert result.mc_number == "123"
    assert result.carrier_name  # non-empty


def test_lookup_carrier_end_to_end_inactive(db_session):
    result = lookup_carrier(db_session, _settings(), "44110")
    assert result is not None
    assert result.status == "inactive"


def test_lookup_carrier_end_to_end_nonexistent(db_session):
    result = lookup_carrier(db_session, _settings(), "99999999")
    assert result is None
