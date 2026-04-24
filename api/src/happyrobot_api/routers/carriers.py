from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.config import Settings, get_settings
from happyrobot_api.db import get_db
from happyrobot_api.fmcsa import lookup_carrier
from happyrobot_api.schemas import CarrierResponse, CarrierResponseBody

router = APIRouter(
    prefix="/api/v1/carriers",
    tags=["carriers"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/find", response_model=CarrierResponse)
def find_carrier(
    mc: str | None = Query(None, description="Motor Carrier number"),
    dot: str | None = Query(None, description="DOT number (not yet supported)"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CarrierResponse:
    if not mc and not dot:
        raise HTTPException(
            status_code=400, detail="Either mc or dot must be provided"
        )
    if dot and not mc:
        # DOT-only lookup can be added later by querying FMCSA differently.
        raise HTTPException(
            status_code=400, detail="DOT-only lookup not yet supported; please provide mc"
        )

    assert mc is not None  # narrowed above
    carrier = lookup_carrier(db, settings, mc)
    if not carrier:
        raise HTTPException(
            status_code=404, detail="Carrier not found with the specified identifiers"
        )
    return CarrierResponse(statusCode=200, body=CarrierResponseBody(carrier=carrier))
