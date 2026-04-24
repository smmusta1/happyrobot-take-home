from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.db import get_db
from happyrobot_api.models import Carrier, Load, Offer
from happyrobot_api.schemas import LogOfferRequest, LogOfferResponse

router = APIRouter(
    prefix="/api/v1/offers",
    tags=["offers"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/log", response_model=LogOfferResponse, status_code=status.HTTP_201_CREATED)
def log_offer(body: LogOfferRequest, db: Session = Depends(get_db)) -> LogOfferResponse:
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

    duplicate = (
        db.query(Offer)
        .filter(
            Offer.mc_number == body.mc_number,
            Offer.load_reference_number == body.load_id,
            Offer.carrier_offer == body.carrier_offer,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail="An identical offer from this carrier already exists for this load",
        )

    prior_count = (
        db.query(Offer)
        .filter(
            Offer.mc_number == body.mc_number,
            Offer.load_reference_number == body.load_id,
        )
        .count()
    )
    db.add(
        Offer(
            mc_number=body.mc_number,
            load_reference_number=body.load_id,
            round_number=prior_count + 1,
            carrier_offer=body.carrier_offer,
            agent_counter=None,
            decision="pending",
            notes=body.notes,
        )
    )
    db.commit()
    return LogOfferResponse(status=201)
