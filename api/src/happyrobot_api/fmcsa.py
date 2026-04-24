"""Client + cache for FMCSA QCMobile carrier lookups.

FMCSA returns raw carrier fields; we translate to the Bridge-spec `status` enum
(active / fail / inactive / in_review / not_set) using the eligibility rule:

  status == "active"    if allowedToOperate == "Y" AND statusCode == "A"
  status == "inactive"  if allowedToOperate == "Y" AND statusCode != "A"
  status == "fail"      if allowedToOperate == "N"
  status == "not_set"   otherwise
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from happyrobot_api.config import Settings
from happyrobot_api.models import Carrier
from happyrobot_api.schemas import Carrier as CarrierSchema

FMCSA_TIMEOUT_SECONDS = 10


def _now() -> datetime:
    """Timezone-naive current UTC time (matches our SQLite DATETIME columns)."""
    return datetime.now(UTC).replace(tzinfo=None)


def _map_eligibility(fmcsa_carrier: dict[str, Any]) -> str:
    allowed = fmcsa_carrier.get("allowedToOperate")
    status_code = fmcsa_carrier.get("statusCode")
    if allowed == "N":
        return "fail"
    if allowed == "Y" and status_code == "A":
        return "active"
    if allowed == "Y":
        return "inactive"
    return "not_set"


def _fmcsa_to_schema(fmcsa_carrier: dict[str, Any], mc_number: str) -> CarrierSchema:
    return CarrierSchema(
        carrier_id=None,
        carrier_name=fmcsa_carrier.get("legalName", "Unknown"),
        status=_map_eligibility(fmcsa_carrier),  # type: ignore[arg-type]
        dot_number=str(fmcsa_carrier["dotNumber"]) if fmcsa_carrier.get("dotNumber") else None,
        mc_number=mc_number,
        contacts=[],
        bridge=None,
    )


def fetch_fmcsa_carrier(settings: Settings, mc_number: str) -> dict[str, Any] | None:
    """Hit FMCSA live. Returns the raw carrier dict, or None if no carrier exists for this MC."""
    url = f"{settings.fmcsa_base_url}/carriers/docket-number/{mc_number}"
    response = httpx.get(
        url,
        params={"webKey": settings.fmcsa_web_key},
        timeout=FMCSA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload.get("content") or []
    if not content:
        return None
    return content[0].get("carrier")


def _cache_is_fresh(carrier: Carrier, cache_hours: int) -> bool:
    return carrier.cached_at > _now() - timedelta(hours=cache_hours)


def lookup_carrier(db: Session, settings: Settings, mc_number: str) -> CarrierSchema | None:
    """Look up a carrier by MC, using our cache first, falling back to FMCSA.

    Returns None if FMCSA has no record of this MC.
    """
    cached = db.query(Carrier).filter_by(mc_number=mc_number).one_or_none()
    if cached and _cache_is_fresh(cached, settings.fmcsa_cache_hours):
        return CarrierSchema(
            carrier_id=str(cached.id),
            carrier_name=cached.carrier_name,
            status=cached.status,  # type: ignore[arg-type]
            dot_number=cached.dot_number,
            mc_number=cached.mc_number,
            contacts=[],
            bridge=None,
        )

    raw = fetch_fmcsa_carrier(settings, mc_number)
    if not raw:
        return None

    schema = _fmcsa_to_schema(raw, mc_number)

    if cached:
        cached.carrier_name = schema.carrier_name
        cached.status = schema.status
        cached.dot_number = schema.dot_number
        cached.allowed_to_operate = raw.get("allowedToOperate") == "Y"
        cached.fmcsa_raw = raw
        cached.cached_at = _now()
    else:
        db.add(
            Carrier(
                mc_number=mc_number,
                dot_number=schema.dot_number,
                carrier_name=schema.carrier_name,
                status=schema.status,
                allowed_to_operate=raw.get("allowedToOperate") == "Y",
                fmcsa_raw=raw,
            )
        )
    db.commit()
    return schema
