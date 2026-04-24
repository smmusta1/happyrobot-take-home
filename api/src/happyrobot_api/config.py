import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    api_key: str
    fmcsa_web_key: str
    fmcsa_cache_hours: int = 24
    fmcsa_base_url: str = "https://mobile.fmcsa.dot.gov/qc/services"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("API_KEY", ""),
        fmcsa_web_key=os.getenv("FMCSA_WEB_KEY", ""),
        fmcsa_cache_hours=int(os.getenv("FMCSA_CACHE_HOURS", "24")),
    )
