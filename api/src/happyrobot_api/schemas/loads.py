from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

EquipmentType = Literal[
    "Dry Van", "Reefer", "Flatbed", "Step Deck", "Box Truck", "Power Only"
]
LoadType = Literal["owned", "can_get"]
LoadStatus = Literal[
    "at_pickup",
    "picked_up",
    "at_delivery",
    "dispatched",
    "delivered",
    "en_route",
    "in_transit",
    "completed",
    "available",
    "covered",
    "unavailable",
]
StopType = Literal["origin", "destination", "pick", "drop"]
BridgeStatus = Literal["success", "failed"]


class Location(BaseModel):
    city: str
    state: str
    zip: str
    country: str


class Stop(BaseModel):
    type: StopType
    location: Location
    stop_timestamp_open: datetime | None = None
    stop_timestamp_close: datetime | None = None


class LoadContact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str
    extension: str | None = None
    type: str | None = None


class LoadBridge(BaseModel):
    status: BridgeStatus
    bridge_load_id: str | None = None


class Load(BaseModel):
    reference_number: str = Field(..., description="Custom identifier for the load")
    contact: LoadContact | None = None
    type: LoadType
    stops: list[Stop]
    max_buy: Decimal
    status: LoadStatus
    is_partial: bool
    is_hazmat: bool
    posted_carrier_rate: Decimal
    sale_notes: str | None = None
    branch: str | None = None
    commodity_type: str
    weight: Decimal | None = None
    number_of_pieces: int | None = None
    miles: int | None = None
    dimensions: str | None = None
    bridge: LoadBridge | None = None
    equipment_type: EquipmentType


class LoadResponseBody(BaseModel):
    load: Load


class LoadResponse(BaseModel):
    """Response envelope for GET /api/v1/loads/{reference_number}."""

    statusCode: int
    body: LoadResponseBody


class LoadsResponseBody(BaseModel):
    loads: list[Load] = Field(..., max_length=3, description="Max 3 results per spec")


class LoadsResponse(BaseModel):
    """Response envelope for GET /api/v1/loads."""

    statusCode: int
    body: LoadsResponseBody
