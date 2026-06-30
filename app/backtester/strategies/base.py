"""BaseStrategy — all backtest strategies inherit from this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Order:
    instrument_id: str
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    order_time: datetime
    signal_price: float | None = None  # expected entry price
    stop_loss: float | None = None
    target: float | None = None


class BaseStrategy(ABC):
    def __init__(self, parameters: dict, initial_capital: float = 500_000.0) -> None:
        self.parameters = parameters
        self.capital = initial_capital
        self.open_positions: list[dict] = []
        self.trades: list[dict] = []

    @abstractmethod
    def on_chain(self, chain: dict, timestamp: datetime) -> list[Order]:
        """Called on each chain snapshot — return orders to execute."""
        ...

    def on_fill(self, order: Order, fill_price: float, commission: float) -> None:
        self.open_positions.append({
            "instrument_id": order.instrument_id,
            "symbol": order.symbol,
            "action": order.action,
            "quantity": order.quantity,
            "entry_price": fill_price,
            "entered_at": order.order_time,
            "stop_loss": order.stop_loss,
            "target": order.target,
            "commission": commission,
        })
        cost = fill_price * order.quantity + commission
        if order.action == "BUY":
            self.capital -= cost

    def close_position(self, position: dict, exit_price: float, exit_time: datetime, reason: str) -> None:
        cost = position["entry_price"] * position["quantity"]
        proceeds = exit_price * position["quantity"]
        multiplier = 1 if position["action"] == "BUY" else -1
        pnl = multiplier * (proceeds - cost) - position.get("commission", 0)
        self.capital += cost + pnl
        self.trades.append({**position, "exit_price": exit_price, "exited_at": exit_time, "exit_reason": reason, "pnl": pnl})
        self.open_positions = [p for p in self.open_positions if p is not position]
