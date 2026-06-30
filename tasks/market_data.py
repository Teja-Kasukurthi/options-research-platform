"""Celery tasks — market data refresh."""

import asyncio
from datetime import datetime

import structlog

from tasks import app

logger = structlog.get_logger(__name__)


@app.task(name="tasks.market_data.refresh_options_chain", bind=True, max_retries=3)
def refresh_options_chain(self, underlyings: list[str] | None = None) -> dict:
    from app.core.calendar import is_market_open
    if not is_market_open():
        return {"skipped": "market_closed"}

    underlyings = underlyings or ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

    async def _run() -> dict:
        from app.market_data.nse import get_nse_scraper
        from app.core.redis import get_redis
        import json

        scraper = get_nse_scraper()
        redis = await get_redis()
        refreshed = []

        for underlying in underlyings:
            chain = await scraper.fetch_options_chain(underlying)
            if chain:
                cache_key = f"options:chain:{underlying}:{chain.expiry}"
                from app.analytics.chain import enrich_chain
                from app.analytics.oi_analysis import compute_oi_analysis
                enriched = enrich_chain(chain)
                oi = compute_oi_analysis(chain)
                payload = {
                    "underlying": chain.underlying,
                    "expiry": chain.expiry,
                    "spot_price": chain.spot_price,
                    "timestamp": chain.timestamp.isoformat(),
                    "strikes": enriched,
                    "pcr": oi.pcr,
                    "max_pain": oi.max_pain,
                }
                await redis.setex(cache_key, 30, json.dumps(payload, default=str))
                await redis.publish("market:chain:updated", json.dumps({"underlying": underlying, "expiry": chain.expiry}))
                refreshed.append(underlying)

        logger.info("chain_refresh_complete", underlyings=refreshed)
        return {"refreshed": refreshed, "timestamp": datetime.now().isoformat()}

    return asyncio.run(_run())


@app.task(name="tasks.market_data.fetch_fii_dii")
def fetch_fii_dii() -> dict:
    async def _run() -> dict:
        from app.market_data.nse import get_nse_scraper
        scraper = get_nse_scraper()
        data = await scraper.fetch_fii_dii()
        if data:
            from app.core.redis import get_redis
            import json
            redis = await get_redis()
            await redis.setex("market:fii_dii:latest", 3600, json.dumps(data))
            logger.info("fii_dii_fetched", date=data.get("date"))
        return data or {}

    return asyncio.run(_run())


@app.task(name="tasks.market_data.ingest_tick")
def ingest_tick(symbol: str, tick_data: dict) -> None:
    """Store tick to DB (called from KiteTickerManager)."""
    # Ticks are stored via Redis pub/sub by KiteTickerManager directly.
    # This task handles DB persistence for OHLCV aggregation if needed.
    pass
