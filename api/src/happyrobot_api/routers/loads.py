from datetime import date, datetime, time
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from happyrobot_api.auth import verify_api_key
from happyrobot_api.db import get_db
from happyrobot_api.models import Load as LoadModel
from happyrobot_api.schemas import (
    Load,
    LoadContact,
    LoadResponse,
    LoadResponseBody,
    LoadsResponse,
    LoadsResponseBody,
    Location,
    Stop,
)
from happyrobot_api.schemas.loads import (
    EquipmentType,
    LoadStatus,
    LoadType,
    StopType,
)

router = APIRouter(
    prefix="/api/v1/loads",
    tags=["loads"],
    dependencies=[Depends(verify_api_key)],
)

MAX_RESULTS = 3


def _to_schema(row: LoadModel) -> Load:
    stops = [
        Stop(
            type=cast(StopType, "origin"),
            location=Location(
                city=row.origin_city,
                state=row.origin_state,
                zip=row.origin_zip,
                country=row.origin_country,
            ),
            stop_timestamp_open=row.origin_open,
            stop_timestamp_close=row.origin_close,
        ),
        Stop(
            type=cast(StopType, "destination"),
            location=Location(
                city=row.destination_city,
                state=row.destination_state,
                zip=row.destination_zip,
                country=row.destination_country,
            ),
            stop_timestamp_open=row.destination_open,
            stop_timestamp_close=row.destination_close,
        ),
    ]
    contact = LoadContact(**row.contact) if row.contact else None
    return Load(
        reference_number=row.reference_number,
        contact=contact,
        type=cast(LoadType, row.type),
        stops=stops,
        max_buy=row.max_buy,
        status=cast(LoadStatus, row.status),
        is_partial=row.is_partial,
        is_hazmat=row.is_hazmat,
        posted_carrier_rate=row.posted_carrier_rate,
        sale_notes=row.sale_notes,
        branch=None,
        commodity_type=row.commodity_type,
        weight=row.weight,
        number_of_pieces=row.number_of_pieces,
        miles=row.miles,
        dimensions=row.dimensions,
        bridge=None,
        equipment_type=cast(EquipmentType, row.equipment_type),
    )


@router.get("", response_model=LoadsResponse)
def search_loads(
    origin_city: str | None = Query(None),
    origin_state: str | None = Query(None),
    destination_city: str | None = Query(None),
    destination_state: str | None = Query(None),
    equipment_type: str | None = Query(None),
    # Accept as str so empty-string values (sent by HappyRobot when a filter is unset)
    # don't trip FastAPI's date validator. Parsed manually below.
    pickup_date: str | None = Query(None),
    # Accepted-but-ignored per Bridge spec ("not all filters required for everyone"):
    reefer_min_temp: float | None = Query(None),
    reefer_max_temp: float | None = Query(None),
    origin_lat: float | None = Query(None),
    origin_lng: float | None = Query(None),
    origin_radius: float | None = Query(None),
    destination_lat: float | None = Query(None),
    destination_lng: float | None = Query(None),
    destination_radius: float | None = Query(None),
    carrier_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> LoadsResponse:
    q = db.query(LoadModel).filter(LoadModel.status == "available")

    if origin_city:
        q = q.filter(func.lower(LoadModel.origin_city) == origin_city.lower())
    if origin_state:
        q = q.filter(func.lower(LoadModel.origin_state) == origin_state.lower())
    if destination_city:
        q = q.filter(func.lower(LoadModel.destination_city) == destination_city.lower())
    if destination_state:
        q = q.filter(func.lower(LoadModel.destination_state) == destination_state.lower())
    if equipment_type:
        q = q.filter(LoadModel.equipment_type == equipment_type)
    if pickup_date:
        try:
            parsed = date.fromisoformat(pickup_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="pickup_date must be ISO format YYYY-MM-DD",
            ) from exc
        day_start = datetime.combine(parsed, time.min)
        day_end = datetime.combine(parsed, time.max)
        q = q.filter(LoadModel.origin_open <= day_end, LoadModel.origin_close >= day_start)

    rows = q.order_by(LoadModel.origin_open.asc()).limit(MAX_RESULTS).all()
    loads = [_to_schema(r) for r in rows]
    return LoadsResponse(statusCode=200, body=LoadsResponseBody(loads=loads))


@router.get("/{reference_number}", response_model=LoadResponse)
def get_load(
    reference_number: str,
    carrier_id: str | None = Query(None),  # accepted per spec; unused in demo
    db: Session = Depends(get_db),
) -> LoadResponse:
    row = db.query(LoadModel).filter(LoadModel.reference_number == reference_number).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Load not found with the specified ID")
    return LoadResponse(statusCode=200, body=LoadResponseBody(load=_to_schema(row)))
