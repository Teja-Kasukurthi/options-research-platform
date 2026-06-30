"""Portfolio state — holdings, cash, MTM P&L."""

from dataclasses import dataclass, field
from datetime import datetime


INITIAL_CAPITAL = 500_000.0  # Rs 5 lakh paper capital


@dataclass
class PortfolioState:
    cash: float = INITIAL_CAPITAL
    open_trade_ids: list[str] = field(default_factory=list)
    total_realized_pnl: float = 0.0

    @property
    def capital_deployed(self) -> float:
        return INITIAL_CAPITAL - self.cash

    @property
    def capital_utilization(self) -> float:
        return self.capital_deployed / INITIAL_CAPITAL
