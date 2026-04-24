from pydantic import BaseModel


class ErrorBody(BaseModel):
    error: str


class ErrorResponse(BaseModel):
    """Standard error envelope for GET endpoints: {statusCode, body:{error}}."""

    statusCode: int
    body: ErrorBody
