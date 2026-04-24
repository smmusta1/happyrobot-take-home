from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class MetricsSummary(BaseModel):
    """High-level KPIs for the dashboard home view."""

    calls_total: int
    calls_today: int
    acceptance_rate: float  # 0.0 – 1.0
    avg_rounds_when_accepted: float | None
    avg_final_rate: Decimal | None
    outcomes: dict[str, int]  # e.g. {"accepted": 12, "declined": 3, ...}
    sentiment: dict[str, int]  # e.g. {"positive": 10, "neutral": 4, "negative": 1}
    calls_by_day: list[dict[str, Any]]  # [{"date": "2026-04-23", "count": 5}, ...]


class CallListItem(BaseModel):
    id: int
    mc_number: str | None
    carrier_name: str | None
    load_id: str | None  # aliased from load_reference_number
    outcome: str | None
    sentiment: str | None
    final_rate: Decimal | None
    rounds_used: int | None
    agreement_reached: bool | None
    created_at: datetime


class CallListResponse(BaseModel):
    calls: list[CallListItem]
    total: int


class OfferItem(BaseModel):
    id: int
    round_number: int
    carrier_offer: Decimal
    agent_counter: Decimal | None
    decision: str
    created_at: datetime


class CallDetail(BaseModel):
    call: CallListItem
    transcript: str | None
    extracted_fields: dict[str, Any] | None
    offers: list[OfferItem]
