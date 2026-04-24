from fastapi import APIRouter, Depends, FastAPI

from happyrobot_api import errors
from happyrobot_api.auth import verify_api_key
from happyrobot_api.routers import calls, carriers, dashboard, loads, negotiate, offers

app = FastAPI(title="HappyRobot Carrier Sales API", version="0.1.0")
errors.register(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


@api_router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
app.include_router(carriers.router)
app.include_router(loads.router)
app.include_router(offers.router)
app.include_router(negotiate.router)
app.include_router(calls.router)
app.include_router(dashboard.router)
