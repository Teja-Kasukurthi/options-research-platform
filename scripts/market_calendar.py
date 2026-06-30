#!/usr/bin/env python3
"""Sync NSE holiday calendar for the current year."""

import asyncio
import httpx
from datetime import datetime


NSE_HOLIDAY_URL = "https://www.nseindia.com/api/holiday-master?type=trading"


async def fetch_nse_holidays() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(NSE_HOLIDAY_URL, headers=headers)
        r.raise_for_status()
        return r.json().get("CM", [])  # CM = Capital Markets segment


async def main() -> None:
    print("Fetching NSE holiday calendar...")
    holidays = await fetch_nse_holidays()

    current_year = datetime.now().year
    dates = []
    for h in holidays:
        try:
            dt = datetime.strptime(h["tradingDate"], "%d-%b-%Y")
            if dt.year == current_year:
                dates.append((dt.strftime("%Y-%m-%d"), h.get("description", "")))
        except (ValueError, KeyError):
            continue

    print(f"\nNSE holidays {current_year}:")
    for d, desc in sorted(dates):
        print(f"  {d}: {desc}")

    # Generate Python set for app/core/calendar.py
    print(f"\nPaste into calendar.py:")
    print(f"NSE_HOLIDAYS_{current_year}: set[date] = {{")
    for d, desc in sorted(dates):
        print(f"    date({d.replace('-', ', ')}),  # {desc}")
    print("}")


if __name__ == "__main__":
    asyncio.run(main())
