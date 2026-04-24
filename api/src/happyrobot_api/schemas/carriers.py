from typing import Literal

from pydantic import BaseModel, Field

CarrierStatus = Literal["active", "fail", "inactive", "in_review", "not_set"]
ContactType = Literal["primary", "dispatch", "billing", "driver", "claims"]
PreferredContactMethod = Literal["email", "phone", "text"]
BridgeStatus = Literal["success", "failed"]


class CarrierContact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    type: ContactType | None = None
    extension: str | None = None
    preferred_contact_method: PreferredContactMethod | None = None


class CarrierBridge(BaseModel):
    status: BridgeStatus
    bridge_carrier_id: str | None = None


class Carrier(BaseModel):
    carrier_id: str | None = None
    carrier_name: str = Field(..., description="Legal name of the carrier")
    status: CarrierStatus = Field(..., description="Current status of the carrier")
    dot_number: str | None = None
    mc_number: str | None = None
    contacts: list[CarrierContact] = []
    bridge: CarrierBridge | None = None


class CarrierResponseBody(BaseModel):
    carrier: Carrier


class CarrierResponse(BaseModel):
    """Response envelope for GET /api/v1/carriers/find."""

    statusCode: int
    body: CarrierResponseBody
