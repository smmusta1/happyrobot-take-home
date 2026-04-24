from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.db import get_db
from happyrobot_api.models import Carrier, Load, Offer
from happyrobot_api.negotiate import MAX_ROUNDS, evaluate_offer
from happyrobot_api.schemas import NegotiateRequest, NegotiateResponse

router = APIRouter(
    prefix="/api/v1/negotiate",
    tags=["negotiate"],
    dependencies=[Depends(verify_api_key)],
)


def _rounds_remaining(round_number: int) -> int:
    return max(MAX_ROUNDS - round_number, 0)


@router.post("", response_model=NegotiateResponse)
def negotiate(body: NegotiateRequest, db: Session = Depends(get_db)) -> NegotiateResponse:
    if body.carrier_offer <= Decimal("0"):
        raise HTTPException(status_code=400, detail="carrier_offer must be greater than zero")

    load = db.query(Load).filter(Load.reference_number == body.load_id).one_or_none()
    if load is None:
        raise HTTPException(status_code=404, detail=f"Load with ID {body.load_id} not found")

    carrier = db.query(Carrier).filter(Carrier.mc_number == body.mc_number).one_or_none()
    if carrier is None:
        raise HTTPException(
            status_code=404, detail=f"Carrier with MC {body.mc_number} not found"
        )

    existing = (
        db.query(Offer)
        .filter(
            Offer.mc_number == body.mc_number,
            Offer.load_reference_number == body.load_id,
            Offer.carrier_offer == body.carrier_offer,
        )
        .first()
    )
    if existing is not None:
        return NegotiateResponse(
            decision=existing.decision,  # type: ignore[arg-type]
            agent_counter=existing.agent_counter,
            round_number=existing.round_number,
            rounds_remaining=_rounds_remaining(existing.round_number),
            message=existing.notes or "",
        )

    prior_offers = (
        db.query(Offer)
        .filter(
            Offer.mc_number == body.mc_number,
            Offer.load_reference_number == body.load_id,
        )
        .order_by(Offer.id.asc())
        .all()
    )
    round_number = len(prior_offers) + 1
    last_agent_counter = next(
        (o.agent_counter for o in reversed(prior_offers) if o.agent_counter is not None),
        None,
    )

    result = evaluate_offer(
        posted_carrier_rate=load.posted_carrier_rate,
        max_buy=load.max_buy,
        carrier_offer=body.carrier_offer,
        round_number=round_number,
        last_agent_counter=last_agent_counter,
    )

    db.add(
        Offer(
            mc_number=body.mc_number,
            load_reference_number=body.load_id,
            round_number=round_number,
            carrier_offer=body.carrier_offer,
            agent_counter=result.agent_counter,
            decision=result.decision,
            notes=body.notes or result.message,
        )
    )
    db.commit()

    return NegotiateResponse(
        decision=result.decision,
        agent_counter=result.agent_counter,
        round_number=round_number,
        rounds_remaining=_rounds_remaining(round_number),
        message=result.message,
    )
