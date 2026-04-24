from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Outcome = Literal[
    "accepted",
    "declined",
    "no_match",
    "ineligible",
    "carrier_dropped",
]
Sentiment = Literal["positive", "neutral", "negative"]


class CallLogRequest(BaseModel):
    """Payload HappyRobot POSTs at end-of-call."""

    external_call_id: str | None = Field(
        None, description="HappyRobot's call session ID — used for idempotent upsert"
    )
    mc_number: str | None = None
    carrier_name: str | None = None
    load_id: str | None = Field(None, description="Reference number of the matched load")
    outcome: Outcome
    sentiment: Sentiment
    final_rate: Decimal | None = None
    rounds_used: int | None = None
    agreement_reached: bool = False
    transcript: str | None = None
    extracted_fields: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_strings(cls, data: Any) -> Any:
        """HappyRobot sends unset fields as empty strings or the literal
        string "null" instead of real JSON null.

        Coerce both → None for optional fields so downstream type validation
        (Decimal, int, bool, etc.) doesn't reject them.
        """
        if not isinstance(data, dict):
            return data
        nullish = {"", "null", "None"}
        nullable = {
            "external_call_id",
            "mc_number",
            "carrier_name",
            "load_id",
            "final_rate",
            "rounds_used",
            "transcript",
        }
        for key in nullable:
            if data.get(key) in nullish:
                data[key] = None
        # agreement_reached defaults to False; treat nullish values as False
        if data.get("agreement_reached") in nullish:
            data["agreement_reached"] = False
        return data


class CallLogResponse(BaseModel):
    status: int = Field(..., description="201 on create, 200 on update")
    call_id: int
    offers_linked: int = Field(
        ..., description="How many prior offer rows were linked to this call"
    )
