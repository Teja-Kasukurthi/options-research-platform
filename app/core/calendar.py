from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.constants import MARKET_CLOSE, MARKET_OPEN

IST = ZoneInfo("Asia/Kolkata")

# NSE holidays — update annually via scripts/market_calendar.py
NSE_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 20),   # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 10, 24),  # Dussehra
    date(2026, 11, 14),  # Diwali Laxmi Puja
    date(2026, 11, 27),  # Gurunanak Jayanti
    date(2026, 12, 25),  # Christmas
}


def is_market_open(dt: datetime | None = None) -> bool:
    now = dt or datetime.now(IST)
    if now.weekday() >= 5:
        return False
    if now.date() in NSE_HOLIDAYS_2026:
        return False
    t = now.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


def next_market_open() -> datetime:
    now = datetime.now(IST)
    candidate = now.replace(hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute, second=0, microsecond=0)
    while True:
        if candidate > now and candidate.weekday() < 5 and candidate.date() not in NSE_HOLIDAYS_2026:
            return candidate
        candidate = candidate.replace(day=candidate.day + 1)
