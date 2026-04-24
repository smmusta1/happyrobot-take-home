from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["accept", "counter", "decline"]


class NegotiateRequest(BaseModel):
    """Request body for POST /api/v1/negotiate."""

    load_id: str = Field(..., description="Reference number of the load")
    mc_number: str = Field(..., description="Carrier MC number")
    carrier_offer: Decimal = Field(..., description="Price offered by the carrier in USD")
    notes: str | None = None


class NegotiateResponse(BaseModel):
    """Response for POST /api/v1/negotiate.

    Custom endpoint — not part of the Bridge API spec. Uses a flat shape that's
    easy for the HappyRobot agent to consume as a tool response.
    """

    decision: Decision
    agent_counter: Decimal | None = Field(
        None, description="The counter/accept amount; null when decision is 'decline'"
    )
    round_number: int = Field(..., description="Which round this offer was (1-based)")
    rounds_remaining: int = Field(..., description="Remaining rounds before last-chance")
    message: str = Field(..., description="Agent-facing summary sentence for speech synthesis")
