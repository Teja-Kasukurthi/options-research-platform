"""Stop-loss watcher and expiry proximity monitor."""

import json
from datetime import date, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from models.paper_trades import PaperTrade
from models.positions import Position
from models.instruments import Instrument

logger = structlog.get_logger(__name__)


async def check_stop_losses(db: AsyncSession) -> list[dict]:
    """Check all open trades for stop-loss and target hits."""
    open_trades_q = await db.execute(
        select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
    )
    open_trades = open_trades_q.scalars().all()

    redis = await get_redis()
    alerts = []

    for trade in open_trades:
        instr = await db.get(Instrument, trade.instrument_id)
        if not instr:
            continue

        cached = await redis.get(f"market:tick:{instr.symbol}")
        if not cached:
            continue

        tick = json.loads(cached)
        ltp = tick.get("ltp", 0)

        if trade.stop_loss and ltp <= trade.stop_loss and trade.action == "BUY":
            alerts.append({
                "trade_id": str(trade.id),
                "symbol": instr.symbol,
                "alert_type": "stop_loss",
                "severity": "critical",
                "ltp": ltp,
                "stop_loss": trade.stop_loss,
                "action": "exit",
            })
            await redis.publish("pubsub:position:alert", json.dumps(alerts[-1]))

        elif trade.target and ltp >= trade.target and trade.action == "BUY":
            alerts.append({
                "trade_id": str(trade.id),
                "symbol": instr.symbol,
                "alert_type": "target",
                "severity": "info",
                "ltp": ltp,
                "target": trade.target,
                "action": "alert",
            })
            await redis.publish("pubsub:position:alert", json.dumps(alerts[-1]))

        # Expiry proximity
        if instr.expiry:
            days_to_expiry = (instr.expiry - date.today()).days
            if days_to_expiry <= 3:
                alert = {
                    "trade_id": str(trade.id),
                    "symbol": instr.symbol,
                    "alert_type": "expiry_near",
                    "severity": "warning",
                    "days_to_expiry": days_to_expiry,
                    "action": "alert",
                }
                alerts.append(alert)
                await redis.publish("pubsub:position:alert", json.dumps(alert))

    if alerts:
        logger.warning("position_alerts", count=len(alerts))
    return alerts
