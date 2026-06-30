"""Zerodha Kite Connect — REST + WebSocket market data."""

import asyncio
import logging
from datetime import datetime
from typing import Callable

import structlog
from kiteconnect import KiteConnect, KiteTicker
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.redis import get_redis
from app.market_data.normalizer import Tick

logger = structlog.get_logger(__name__)

_kite: KiteConnect | None = None


def get_kite() -> KiteConnect:
    global _kite
    if _kite is None:
        _kite = KiteConnect(api_key=settings.kite_api_key)
        _kite.set_access_token(settings.kite_access_token)
    return _kite


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_quote(symbols: list[str]) -> dict:
    return get_kite().quote(symbols)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ohlcv(instrument_token: int, interval: str, from_dt: datetime, to_dt: datetime) -> list[dict]:
    return get_kite().historical_data(instrument_token, from_dt, to_dt, interval)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_instruments(exchange: str = "NFO") -> list[dict]:
    return get_kite().instruments(exchange)


class KiteTickerManager:
    """Manages Kite WebSocket, republishes ticks to Redis pub/sub."""

    def __init__(self) -> None:
        self._ticker: KiteTicker | None = None
        self._subscribed_tokens: set[int] = set()
        self._on_tick_callbacks: list[Callable[[list[dict]], None]] = []

    def start(self, tokens: list[int]) -> None:
        self._ticker = KiteTicker(settings.kite_api_key, settings.kite_access_token)
        self._subscribed_tokens = set(tokens)

        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_connect = self._on_connect
        self._ticker.on_close = self._on_close
        self._ticker.on_error = self._on_error
        self._ticker.on_reconnect = self._on_reconnect

        self._ticker.connect(threaded=True)

    def stop(self) -> None:
        if self._ticker:
            self._ticker.stop()

    def _on_connect(self, ws: object, response: object) -> None:
        logger.info("kite_ws_connected")
        if self._ticker:
            self._ticker.subscribe(list(self._subscribed_tokens))
            self._ticker.set_mode(self._ticker.MODE_FULL, list(self._subscribed_tokens))

    def _on_close(self, ws: object, code: int, reason: str) -> None:
        logger.warning("kite_ws_closed", code=code, reason=reason)

    def _on_error(self, ws: object, code: int, reason: str) -> None:
        logger.error("kite_ws_error", code=code, reason=reason)

    def _on_reconnect(self, ws: object, attempts_count: int) -> None:
        logger.info("kite_ws_reconnecting", attempt=attempts_count)

    def _on_ticks(self, ws: object, ticks: list[dict]) -> None:
        asyncio.run(self._publish_ticks(ticks))

    async def _publish_ticks(self, ticks: list[dict]) -> None:
        redis = await get_redis()
        for tick in ticks:
            symbol = str(tick.get("instrument_token", ""))
            payload = {
                "ltp": tick.get("last_price", 0),
                "bid": tick.get("depth", {}).get("buy", [{}])[0].get("price", 0),
                "ask": tick.get("depth", {}).get("sell", [{}])[0].get("price", 0),
                "volume": tick.get("volume", 0),
                "oi": tick.get("oi", 0),
                "ts": tick.get("exchange_timestamp", datetime.now()).isoformat(),
            }
            import json
            await redis.setex(f"market:tick:{symbol}", 5, json.dumps(payload))
            await redis.publish(f"pubsub:tick:{symbol}", json.dumps(payload))


_ticker_manager: KiteTickerManager | None = None


def get_ticker_manager() -> KiteTickerManager:
    global _ticker_manager
    if _ticker_manager is None:
        _ticker_manager = KiteTickerManager()
    return _ticker_manager
