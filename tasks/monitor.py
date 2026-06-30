"""Celery tasks — position monitor."""

import asyncio

import structlog

from tasks import app

logger = structlog.get_logger(__name__)


@app.task(name="tasks.monitor.check_positions", bind=True)
def check_positions(self) -> dict:
    from app.core.calendar import is_market_open
    if not is_market_open():
        return {"skipped": "market_closed"}

    async def _run() -> dict:
        from app.monitor.watcher import check_stop_losses
        from app.monitor.greeks_live import refresh_position_greeks
        from app.core.db import AsyncSessionLocal
        from app.notification.telegram import send_stop_loss_alert

        async with AsyncSessionLocal() as db:
            alerts = await check_stop_losses(db)
            await refresh_position_greeks(db)

        # Send Telegram alerts for critical events
        for alert in alerts:
            if alert.get("severity") == "critical" and alert.get("alert_type") == "stop_loss":
                await send_stop_loss_alert(
                    trade_id=alert["trade_id"],
                    symbol=alert["symbol"],
                    ltp=alert.get("ltp", 0),
                    stop_loss=alert.get("stop_loss", 0),
                )

        return {"alerts": len(alerts)}

    return asyncio.run(_run())


@app.task(name="tasks.monitor.reconcile_pnl")
def reconcile_pnl() -> dict:
    """Daily P&L reconciliation — close expired positions."""

    async def _run() -> dict:
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import select
        from models.paper_trades import PaperTrade
        from models.instruments import Instrument
        from datetime import date, datetime

        async with AsyncSessionLocal() as db:
            open_q = await db.execute(
                select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
            )
            open_trades = open_q.scalars().all()
            closed = 0

            for trade in open_trades:
                instr = await db.get(Instrument, trade.instrument_id)
                if instr and instr.expiry and instr.expiry <= date.today():
                    # Auto-close at 0 (expired worthless) or settlement
                    trade.exit_price = 0.0
                    trade.exited_at = datetime.now()
                    trade.exit_reason = "expiry"
                    trade.realized_pnl = -(trade.entry_price * trade.quantity)
                    trade.unrealized_pnl = 0.0
                    closed += 1

            await db.commit()
            logger.info("pnl_reconcile_complete", expired_closed=closed)
            return {"expired_closed": closed}

    return asyncio.run(_run())
