import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.paper import ExecuteTradeIn, PaperTradeOut, PortfolioOut
from app.core.db import get_db
from app.core.redis import get_redis
from models.paper_trades import PaperTrade
from models.positions import Position
from models.instruments import Instrument
from models.signals import Signal

import json

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/portfolio", response_model=PortfolioOut)
async def get_portfolio(db: AsyncSession = Depends(get_db)) -> PortfolioOut:
    open_trades_q = await db.execute(
        select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
    )
    open_trades = open_trades_q.scalars().all()

    all_trades_q = await db.execute(select(PaperTrade))
    all_trades = all_trades_q.scalars().all()

    total_unrealized = sum(t.unrealized_pnl or 0.0 for t in open_trades)
    total_realized = sum(t.realized_pnl or 0.0 for t in all_trades if t.realized_pnl)

    # Aggregate Greeks from open positions
    positions_q = await db.execute(
        select(Position).where(
            Position.paper_trade_id.in_([t.id for t in open_trades])
        )
    )
    positions = positions_q.scalars().all()
    port_delta = sum(p.delta or 0.0 for p in positions)
    port_theta = sum(p.theta or 0.0 for p in positions)
    port_vega = sum(p.vega or 0.0 for p in positions)
    capital_used = sum(t.entry_price * t.quantity for t in open_trades)

    return PortfolioOut(
        open_trades=len(open_trades),
        total_unrealized_pnl=total_unrealized,
        total_realized_pnl=total_realized,
        portfolio_delta=port_delta,
        portfolio_theta=port_theta,
        portfolio_vega=port_vega,
        capital_used=capital_used,
        positions=[PaperTradeOut.model_validate(t) for t in open_trades],
    )


@router.get("/trades", response_model=list[PaperTradeOut])
async def list_trades(
    open_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[PaperTradeOut]:
    q = select(PaperTrade).order_by(PaperTrade.entered_at.desc()).limit(limit)
    if open_only:
        q = q.where(PaperTrade.exited_at == None)  # noqa: E711
    result = await db.execute(q)
    return [PaperTradeOut.model_validate(t) for t in result.scalars().all()]


@router.get("/trades/{trade_id}", response_model=PaperTradeOut)
async def get_trade(trade_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PaperTradeOut:
    t = await db.get(PaperTrade, trade_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found")
    return PaperTradeOut.model_validate(t)


@router.post("/trades/{signal_id}/execute", response_model=PaperTradeOut)
async def execute_trade(
    signal_id: uuid.UUID,
    body: ExecuteTradeIn,
    db: AsyncSession = Depends(get_db),
) -> PaperTradeOut:
    from app.market_data.kite import fetch_quote
    from app.core.constants import SLIPPAGE_BPS
    from datetime import datetime

    instr = await db.get(Instrument, body.instrument_id)
    if not instr:
        raise HTTPException(status_code=404, detail="Instrument not found")

    # Fetch current price
    try:
        quotes = fetch_quote([f"NFO:{instr.symbol}"])
        q_data = quotes.get(f"NFO:{instr.symbol}", {})
        bid = q_data.get("depth", {}).get("buy", [{}])[0].get("price", 0)
        ask = q_data.get("depth", {}).get("sell", [{}])[0].get("price", 0)
        oi = q_data.get("oi", 0)

        spread_pct = abs(ask - bid) / ask if ask else 0
        if oi > 1000 and spread_pct < 0.01:
            fill_price = (bid + ask) / 2 + (ask - bid) * 0.5
        elif oi > 200:
            fill_price = ask
        else:
            fill_price = ask * 1.005
    except Exception:
        raise HTTPException(status_code=503, detail="Market data unavailable for execution")

    trade = PaperTrade(
        signal_id=signal_id if body.signal_id else None,
        instrument_id=body.instrument_id,
        action=body.action.upper(),
        entry_price=fill_price,
        quantity=body.quantity,
        stop_loss=body.stop_loss,
        target=body.target,
        entered_at=datetime.now(),
    )
    db.add(trade)
    await db.flush()

    pos = Position(paper_trade_id=trade.id, current_price=fill_price)
    db.add(pos)

    # Update signal status
    sig = await db.get(Signal, signal_id)
    if sig and sig.status == "approved":
        sig.status = "executed"

    await db.commit()
    await db.refresh(trade)

    redis = await get_redis()
    await redis.publish("pubsub:pnl", json.dumps({"event": "trade_opened", "trade_id": str(trade.id)}))

    return PaperTradeOut.model_validate(trade)


@router.post("/trades/{trade_id}/close", response_model=PaperTradeOut)
async def close_trade(
    trade_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PaperTradeOut:
    from datetime import datetime
    from app.market_data.kite import fetch_quote

    trade = await db.get(PaperTrade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.exited_at:
        raise HTTPException(status_code=409, detail="Trade already closed")

    instr = await db.get(Instrument, trade.instrument_id)
    try:
        quotes = fetch_quote([f"NFO:{instr.symbol}"])
        q_data = quotes.get(f"NFO:{instr.symbol}", {})
        exit_price = q_data.get("last_price", trade.entry_price)
    except Exception:
        exit_price = trade.entry_price

    multiplier = 1 if trade.action == "BUY" else -1
    trade.exit_price = exit_price
    trade.exited_at = datetime.now()
    trade.exit_reason = "manual_close"
    trade.realized_pnl = multiplier * (exit_price - trade.entry_price) * trade.quantity
    trade.unrealized_pnl = 0.0

    await db.commit()
    await db.refresh(trade)
    return PaperTradeOut.model_validate(trade)
