"""Error envelopes for /api/v1/*.

Two shapes, by path:

- Flat    `{status, error}`             — for POST write endpoints that match
                                          the Bridge spec's flat shape
                                          (/offers/log, /calls/log)
- Nested  `{statusCode, body: {error}}` — for GET endpoints (carriers, loads,
                                          dashboard) and /negotiate

Routes outside /api/v1 (e.g. /health) keep FastAPI's default behavior.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

FLAT_ENVELOPE_PATHS = {"/api/v1/offers/log", "/api/v1/calls/log"}


def _bridge_envelope(request: Request, status_code: int, message: str) -> JSONResponse | None:
    path = request.url.path
    if path in FLAT_ENVELOPE_PATHS:
        return JSONResponse(
            status_code=status_code,
            content={"status": status_code, "error": message},
        )
    if path.startswith("/api/v1/"):
        return JSONResponse(
            status_code=status_code,
            content={"statusCode": status_code, "body": {"error": message}},
        )
    return None


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    envelope = _bridge_envelope(request, exc.status_code, message)
    if envelope is not None:
        return envelope
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []))
    msg = first.get("msg", "Invalid request")
    message = f"{loc}: {msg}" if loc else msg
    envelope = _bridge_envelope(request, 422, message)
    if envelope is not None:
        return envelope
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


def register(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
