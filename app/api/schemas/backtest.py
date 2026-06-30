from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class BacktestRunIn(BaseModel):
    strategy_name: str
    parameters: dict = {}
    from_date: date
    to_date: date
    initial_capital: float = 500_000.0


class BacktestRunOut(BaseModel):
    id: UUID
    strategy_name: str
    parameters: dict
    from_date: date
    to_date: date
    total_return: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown: float | None
    win_rate: float | None
    total_trades: int | None
    status: str
    ran_at: datetime
    completed_at: datetime | None
    full_metrics: dict | None

    model_config = {"from_attributes": True}
