"""Historical fill simulator — uses options_chain_snapshot bid/ask."""

from dataclasses import dataclass
from datetime import datetime

from app.paper_trader.fill_engine import compute_fill_price


@dataclass
class Fill:
    instrument_id: str
    symbol: str
    action: str
    quantity: int
    fill_price: float
    fill_time: datetime
    liquidity_tier: str
    commission: float  # STT + brokerage approximation


STT_SELL_PCT = 0.0005  # 0.05% STT on sell side (options)
BROKERAGE_PER_LOT = 20.0  # Rs 20 flat per lot (Zerodha-like)


def simulate_fill(
    instrument_id: str,
    symbol: str,
    action: str,
    quantity: int,
    lot_size: int,
    bid: float,
    ask: float,
    oi: int,
    fill_time: datetime,
) -> Fill:
    fill_price, tier = compute_fill_price(bid, ask, oi, action)
    lots = quantity // lot_size
    commission = BROKERAGE_PER_LOT * lots
    if action == "SELL":
        commission += fill_price * quantity * STT_SELL_PCT

    return Fill(
        instrument_id=instrument_id,
        symbol=symbol,
        action=action,
        quantity=quantity,
        fill_price=fill_price,
        fill_time=fill_time,
        liquidity_tier=tier,
        commission=round(commission, 2),
    )
