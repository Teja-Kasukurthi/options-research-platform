"""WebSocket handlers — relay Redis pub/sub to connected browser clients."""

import asyncio
import json

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.redis import get_redis

logger = structlog.get_logger(__name__)


async def _relay(ws: WebSocket, redis: Redis, channel: str) -> None:
    async with redis.pubsub() as ps:
        await ps.subscribe(channel)
        try:
            async for message in ps.listen():
                if message["type"] == "message":
                    await ws.send_text(message["data"])
        except WebSocketDisconnect:
            pass
        finally:
            await ps.unsubscribe(channel)


async def ws_ticks(ws: WebSocket, symbol: str) -> None:
    await ws.accept()
    redis = await get_redis()
    # Send cached last tick immediately
    cached = await redis.get(f"market:tick:{symbol.upper()}")
    if cached:
        await ws.send_text(cached)
    await _relay(ws, redis, f"pubsub:tick:{symbol.upper()}")


async def ws_pnl(ws: WebSocket) -> None:
    await ws.accept()
    redis = await get_redis()
    await _relay(ws, redis, "pubsub:pnl")


async def ws_position_alerts(ws: WebSocket) -> None:
    await ws.accept()
    redis = await get_redis()
    await _relay(ws, redis, "pubsub:position:alert")


async def ws_signals(ws: WebSocket) -> None:
    await ws.accept()
    redis = await get_redis()
    await _relay(ws, redis, "pubsub:signal:new")
