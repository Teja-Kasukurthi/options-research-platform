"""Injectable simulation clock — swaps datetime.now() for replay/backtest."""

from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class ClockProvider:
    """Base clock — live mode returns real time."""

    def now(self) -> datetime:
        return datetime.now(IST)


class SimulatedClock(ClockProvider):
    """Backtest/replay mode — advances on tick."""

    def __init__(self, start: datetime) -> None:
        self._current = start

    def now(self) -> datetime:
        return self._current

    def advance(self, dt: datetime) -> None:
        self._current = dt


_clock: ClockProvider = ClockProvider()


def get_clock() -> ClockProvider:
    return _clock


def set_clock(clock: ClockProvider) -> None:
    global _clock
    _clock = clock
