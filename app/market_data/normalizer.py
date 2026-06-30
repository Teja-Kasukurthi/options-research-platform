from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tick:
    symbol: str
    ltp: float
    bid: float
    ask: float
    volume: int
    oi: int
    timestamp: datetime


@dataclass
class OptionStrike:
    strike: float
    ce_ltp: float | None
    ce_bid: float | None
    ce_ask: float | None
    ce_oi: int | None
    ce_volume: int | None
    ce_iv: float | None
    pe_ltp: float | None
    pe_bid: float | None
    pe_ask: float | None
    pe_oi: int | None
    pe_volume: int | None
    pe_iv: float | None


@dataclass
class OptionsChain:
    underlying: str
    expiry: str  # YYYY-MM-DD
    spot_price: float
    timestamp: datetime
    strikes: list[OptionStrike]

    @property
    def atm_strike(self) -> float:
        strikes = [s.strike for s in self.strikes]
        return min(strikes, key=lambda x: abs(x - self.spot_price))

    def total_ce_oi(self) -> int:
        return sum(s.ce_oi or 0 for s in self.strikes)

    def total_pe_oi(self) -> int:
        return sum(s.pe_oi or 0 for s in self.strikes)

    def pcr(self) -> float | None:
        ce = self.total_ce_oi()
        if ce == 0:
            return None
        return self.total_pe_oi() / ce
