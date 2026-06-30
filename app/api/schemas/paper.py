from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExecuteTradeIn(BaseModel):
    signal_id: UUID | None = None
    instrument_id: UUID
    action: str  # BUY or SELL
    quantity: int = Field(gt=0)
    stop_loss: float | None = None
    target: float | None = None


class PaperTradeOut(BaseModel):
    id: UUID
    instrument_id: UUID
    signal_id: UUID | None
    action: str
    entry_price: float
    quantity: int
    entered_at: datetime
    exit_price: float | None
    exited_at: datetime | None
    realized_pnl: float | None
    unrealized_pnl: float | None
    exit_reason: str | None
    stop_loss: float | None
    target: float | None

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    open_trades: int
    total_unrealized_pnl: float
    total_realized_pnl: float
    portfolio_delta: float | None
    portfolio_theta: float | None
    portfolio_vega: float | None
    capital_used: float
    positions: list[PaperTradeOut]
