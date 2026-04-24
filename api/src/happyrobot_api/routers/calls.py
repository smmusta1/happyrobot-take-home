from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.db import get_db
from happyrobot_api.models import Call, Offer
from happyrobot_api.schemas import CallLogRequest, CallLogResponse

router = APIRouter(
    prefix="/api/v1/calls",
    tags=["calls"],
    dependencies=[Depends(verify_api_key)],
)


def _apply(call: Call, body: CallLogRequest) -> None:
    call.mc_number = body.mc_number
    call.carrier_name = body.carrier_name
    call.load_reference_number = body.load_id
    call.outcome = body.outcome
    call.sentiment = body.sentiment
    call.final_rate = body.final_rate
    call.rounds_used = body.rounds_used
    call.agreement_reached = body.agreement_reached
    call.transcript = body.transcript
    call.extracted_fields = body.extracted_fields


def _link_offers(db: Session, call: Call) -> int:
    if not (call.mc_number and call.load_reference_number):
        return 0
    rows = (
        db.query(Offer)
        .filter(
            Offer.mc_number == call.mc_number,
            Offer.load_reference_number == call.load_reference_number,
            Offer.call_id.is_(None),
        )
        .all()
    )
    for offer in rows:
        offer.call_id = call.id
    return len(rows)


@router.post("/log", response_model=CallLogResponse)
def log_call(
    body: CallLogRequest, response: Response, db: Session = Depends(get_db)
) -> CallLogResponse:
    existing = None
    if body.external_call_id:
        existing = (
            db.query(Call)
            .filter(Call.external_call_id == body.external_call_id)
            .one_or_none()
        )

    if existing is not None:
        _apply(existing, body)
        db.flush()
        linked = _link_offers(db, existing)
        db.commit()
        response.status_code = status.HTTP_200_OK
        return CallLogResponse(status=200, call_id=existing.id, offers_linked=linked)

    call = Call(external_call_id=body.external_call_id)
    _apply(call, body)
    db.add(call)
    db.flush()  # populate call.id
    linked = _link_offers(db, call)
    db.commit()
    db.refresh(call)
    response.status_code = status.HTTP_201_CREATED
    return CallLogResponse(status=201, call_id=call.id, offers_linked=linked)
