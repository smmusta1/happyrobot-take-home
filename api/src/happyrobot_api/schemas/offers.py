from decimal import Decimal

from pydantic import BaseModel, Field


class LogOfferRequest(BaseModel):
    """Request body for POST /api/v1/offers/log."""

    load_id: str = Field(..., description="Reference number of the load")
    mc_number: str = Field(..., description="Carrier MC number")
    carrier_offer: Decimal = Field(..., description="Price offered by the carrier in USD")
    notes: str | None = None


class LogOfferResponse(BaseModel):
    """Response envelope for POST /api/v1/offers/log. Note: flat envelope, not {statusCode,body}."""

    status: int
