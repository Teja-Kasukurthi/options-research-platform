"""Settings router — persists user-configurable risk parameters in Redis."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import verify_jwt
from app.core.redis import get_redis

router = APIRouter(dependencies=[Depends(verify_jwt)])

SETTINGS_KEY = "app:settings"

_DEFAULTS: dict = {
    "watchlist": ["NIFTY", "BANKNIFTY"],
    "max_positions": 5,
    "max_capital_pct_per_trade": 2.0,
    "sector_concentration_pct": 40.0,
    "max_delta": 50_000.0,
    "stop_loss_required": True,
    "min_rr_ratio": 1.5,
    "min_days_to_expiry": 7,
    "max_bid_ask_spread_pct": 2.0,
    "kelly_fraction": 0.25,
    "telegram_alerts": True,
    "email_alerts": False,
}


class Settings(BaseModel):
    watchlist: list[str] = Field(default=["NIFTY", "BANKNIFTY"])
    max_positions: int = Field(default=5, ge=1, le=20)
    max_capital_pct_per_trade: float = Field(default=2.0, gt=0, le=10)
    sector_concentration_pct: float = Field(default=40.0, gt=0, le=100)
    max_delta: float = Field(default=50_000.0)
    stop_loss_required: bool = True
    min_rr_ratio: float = Field(default=1.5, ge=1.0)
    min_days_to_expiry: int = Field(default=7, ge=0)
    max_bid_ask_spread_pct: float = Field(default=2.0, gt=0)
    kelly_fraction: float = Field(default=0.25, gt=0, le=1)
    telegram_alerts: bool = True
    email_alerts: bool = False


async def _load() -> dict:
    redis = await get_redis()
    raw = await redis.get(SETTINGS_KEY)
    if not raw:
        return _DEFAULTS.copy()
    import json
    return {**_DEFAULTS, **json.loads(raw)}


@router.get("/", response_model=Settings)
async def get_settings() -> Settings:
    data = await _load()
    return Settings(**data)


@router.post("/", response_model=Settings)
async def save_settings(body: Settings) -> Settings:
    import json
    redis = await get_redis()
    await redis.set(SETTINGS_KEY, json.dumps(body.model_dump()))
    return body
