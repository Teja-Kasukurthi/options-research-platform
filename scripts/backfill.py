#!/usr/bin/env python3
"""Backfill historical OHLCV data from Kite Connect."""

import asyncio
from datetime import date, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


async def backfill_ohlcv(
    symbols: list[str],
    from_date: date,
    to_date: date | None = None,
) -> None:
    from app.core.db import AsyncSessionLocal
    from app.market_data.kite import fetch_instruments, fetch_ohlcv
    from models.instruments import Instrument
    from models.ohlcv import OHLCV1Min
    from sqlalchemy import select

    to_date = to_date or date.today()

    async with AsyncSessionLocal() as db:
        for symbol in symbols:
            logger.info("backfill_start", symbol=symbol, from_date=from_date, to_date=to_date)

            instr_q = await db.execute(
                select(Instrument).where(
                    Instrument.symbol == symbol.upper(),
                    Instrument.is_active == True,  # noqa: E712
                )
            )
            instr = instr_q.scalars().first()
            if not instr or not instr.kite_instrument_token:
                logger.warning("instrument_not_found", symbol=symbol)
                continue

            # Kite historical data limit: 60 days per request for 1m
            chunk_days = 60
            current = from_date
            while current < to_date:
                chunk_end = min(current + timedelta(days=chunk_days), to_date)
                try:
                    bars = fetch_ohlcv(
                        instr.kite_instrument_token, "minute",
                        datetime.combine(current, datetime.min.time()),
                        datetime.combine(chunk_end, datetime.max.time()),
                    )
                    for bar in bars:
                        db.add(OHLCV1Min(
                            instrument_id=instr.id,
                            time=bar["date"],
                            open=bar["open"],
                            high=bar["high"],
                            low=bar["low"],
                            close=bar["close"],
                            volume=bar.get("volume", 0),
                            oi=bar.get("oi", 0),
                        ))
                    await db.commit()
                    logger.info("backfill_chunk", symbol=symbol, start=current, bars=len(bars))
                except Exception:
                    logger.exception("backfill_chunk_error", symbol=symbol, start=current)

                current = chunk_end + timedelta(days=1)


async def main() -> None:
    import sys
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["NIFTY", "BANKNIFTY"]
    from_date = date(2024, 1, 1)
    logger.info("backfill_start", symbols=symbols, from_date=from_date)
    await backfill_ohlcv(symbols, from_date)
    logger.info("backfill_complete")


if __name__ == "__main__":
    asyncio.run(main())
