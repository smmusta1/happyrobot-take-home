"""Read-side endpoints for the metrics dashboard.

All routes require Bearer auth. The dashboard is a separate service that
authenticates server-side with the same API_KEY; end users never see the key.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.db import get_db
from happyrobot_api.models import Call, Offer
from happyrobot_api.schemas import (
    CallDetail,
    CallListItem,
    CallListResponse,
    MetricsSummary,
    OfferItem,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["dashboard"],
    dependencies=[Depends(verify_api_key)],
)


def _to_item(call: Call) -> CallListItem:
    return CallListItem(
        id=call.id,
        mc_number=call.mc_number,
        carrier_name=call.carrier_name,
        load_id=call.load_reference_number,
        outcome=call.outcome,
        sentiment=call.sentiment,
        final_rate=call.final_rate,
        rounds_used=call.rounds_used,
        agreement_reached=call.agreement_reached,
        created_at=call.created_at,
    )


@router.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(db: Session = Depends(get_db)) -> MetricsSummary:
    all_calls = db.query(Call).all()
    total = len(all_calls)

    # "Today" in UTC — simple and predictable for demo purposes
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    day_start = datetime(now_naive.year, now_naive.month, now_naive.day)
    calls_today = sum(1 for c in all_calls if c.created_at >= day_start)

    accepted = [c for c in all_calls if c.outcome == "accepted"]
    acceptance_rate = (len(accepted) / total) if total else 0.0

    rounds_samples = [c.rounds_used for c in accepted if c.rounds_used is not None]
    avg_rounds = (sum(rounds_samples) / len(rounds_samples)) if rounds_samples else None

    rate_samples = [c.final_rate for c in accepted if c.final_rate is not None]
    avg_final = (sum(rate_samples) / Decimal(len(rate_samples))) if rate_samples else None

    outcomes: dict[str, int] = {}
    sentiment: dict[str, int] = {}
    for c in all_calls:
        if c.outcome:
            outcomes[c.outcome] = outcomes.get(c.outcome, 0) + 1
        if c.sentiment:
            sentiment[c.sentiment] = sentiment.get(c.sentiment, 0) + 1

    # Calls grouped by day for the last 14 days
    since = day_start - timedelta(days=13)
    by_day_counts: dict[str, int] = {}
    for c in all_calls:
        if c.created_at >= since:
            key = c.created_at.strftime("%Y-%m-%d")
            by_day_counts[key] = by_day_counts.get(key, 0) + 1
    calls_by_day = [
        {"date": (since + timedelta(days=i)).strftime("%Y-%m-%d"),
         "count": by_day_counts.get((since + timedelta(days=i)).strftime("%Y-%m-%d"), 0)}
        for i in range(14)
    ]

    return MetricsSummary(
        calls_total=total,
        calls_today=calls_today,
        acceptance_rate=round(acceptance_rate, 4),
        avg_rounds_when_accepted=round(avg_rounds, 2) if avg_rounds is not None else None,
        avg_final_rate=avg_final.quantize(Decimal("0.01")) if avg_final is not None else None,
        outcomes=outcomes,
        sentiment=sentiment,
        calls_by_day=calls_by_day,
    )


@router.get("/calls", response_model=CallListResponse)
def list_calls(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> CallListResponse:
    total = db.query(func.count(Call.id)).scalar() or 0
    rows = (
        db.query(Call)
        .order_by(Call.created_at.desc(), Call.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return CallListResponse(calls=[_to_item(c) for c in rows], total=total)


@router.delete("/calls/{call_id}", status_code=204)
def delete_call(call_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a Call row and cascade to its offers. Primarily for cleaning
    up test-noise rows from the dashboard without shelling into Railway."""
    call = db.query(Call).filter(Call.id == call_id).one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    db.delete(call)
    db.commit()


@router.get("/calls/{call_id}", response_model=CallDetail)
def get_call(call_id: int, db: Session = Depends(get_db)) -> CallDetail:
    call = db.query(Call).filter(Call.id == call_id).one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    offers = (
        db.query(Offer)
        .filter(Offer.call_id == call_id)
        .order_by(Offer.round_number.asc())
        .all()
    )
    return CallDetail(
        call=_to_item(call),
        transcript=call.transcript,
        extracted_fields=call.extracted_fields,
        offers=[
            OfferItem(
                id=o.id,
                round_number=o.round_number,
                carrier_offer=o.carrier_offer,
                agent_counter=o.agent_counter,
                decision=o.decision,
                created_at=o.created_at,
            )
            for o in offers
        ],
    )
