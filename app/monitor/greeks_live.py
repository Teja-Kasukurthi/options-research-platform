"""Live Greeks refresh for all open positions."""

from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.nse import get_nse_scraper
from app.paper_trader.pnl import compute_position_greeks, compute_unrealized_pnl
from models.instruments import Instrument
from models.paper_trades import PaperTrade
from models.positions import Position

logger = structlog.get_logger(__name__)


async def refresh_position_greeks(db: AsyncSession) -> int:
    open_trades_q = await db.execute(
        select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
    )
    open_trades = open_trades_q.scalars().all()
    updated = 0

    for trade in open_trades:
        instr = await db.get(Instrument, trade.instrument_id)
        if not instr or not instr.option_type or not instr.underlying or not instr.expiry:
            continue

        scraper = get_nse_scraper()
        chain = await scraper.fetch_options_chain(instr.underlying, instr.expiry)
        if not chain:
            continue

        # Find current price from chain
        opt_type = instr.option_type.lower()[0]
        current_price = None
        for s in chain.strikes:
            if s.strike == instr.strike:
                current_price = s.ce_ltp if opt_type == "c" else s.pe_ltp
                break

        if not current_price:
            continue

        # Compute Greeks
        from app.core.constants import LOT_SIZES
        lot_size = LOT_SIZES.get(instr.underlying, 1)
        greeks = compute_position_greeks(
            opt_type, chain.spot_price, instr.strike or 0,
            instr.expiry, current_price, trade.quantity, lot_size,
        )

        # Update position
        pos_q = await db.execute(
            select(Position).where(Position.paper_trade_id == trade.id)
        )
        pos = pos_q.scalars().first()
        if pos:
            pos.current_price = current_price
            pos.delta = greeks.get("delta")
            pos.gamma = greeks.get("gamma")
            pos.theta = greeks.get("theta")
            pos.vega = greeks.get("vega")
            pos.iv = greeks.get("iv")

        # Update unrealized P&L
        trade.unrealized_pnl = compute_unrealized_pnl(
            trade.action, trade.entry_price, current_price, trade.quantity
        )
        updated += 1

    await db.commit()
    logger.info("greeks_refresh_complete", updated=updated)
    return updated
