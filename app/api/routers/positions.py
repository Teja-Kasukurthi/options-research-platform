import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.core.db import get_db
from models.positions import Position
from models.paper_trades import PaperTrade

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("")
async def list_positions(db: AsyncSession = Depends(get_db)) -> list[dict]:
    open_trades = await db.execute(
        select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
    )
    trades = open_trades.scalars().all()
    trade_ids = [t.id for t in trades]

    positions = await db.execute(
        select(Position).where(Position.paper_trade_id.in_(trade_ids))
    )
    pos_map = {p.paper_trade_id: p for p in positions.scalars().all()}

    result = []
    for trade in trades:
        pos = pos_map.get(trade.id)
        result.append({
            "trade_id": str(trade.id),
            "instrument_id": str(trade.instrument_id),
            "action": trade.action,
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "unrealized_pnl": trade.unrealized_pnl,
            "stop_loss": trade.stop_loss,
            "target": trade.target,
            "current_price": pos.current_price if pos else None,
            "delta": pos.delta if pos else None,
            "gamma": pos.gamma if pos else None,
            "theta": pos.theta if pos else None,
            "vega": pos.vega if pos else None,
            "iv": pos.iv if pos else None,
            "updated_at": pos.updated_at.isoformat() if pos else None,
        })
    return result


@router.get("/{position_id}")
async def get_position(position_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    pos = await db.get(Position, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    trade = await db.get(PaperTrade, pos.paper_trade_id)
    return {
        "position_id": str(pos.id),
        "trade_id": str(pos.paper_trade_id),
        "current_price": pos.current_price,
        "delta": pos.delta,
        "gamma": pos.gamma,
        "theta": pos.theta,
        "vega": pos.vega,
        "iv": pos.iv,
        "updated_at": pos.updated_at.isoformat(),
        "trade": {
            "action": trade.action if trade else None,
            "entry_price": trade.entry_price if trade else None,
            "quantity": trade.quantity if trade else None,
            "unrealized_pnl": trade.unrealized_pnl if trade else None,
        },
    }
