"""Celery tasks — AI agent runs."""

import asyncio

import structlog

from tasks import app

logger = structlog.get_logger(__name__)


@app.task(name="tasks.agents.run_research_cycle", bind=True, max_retries=2)
def run_research_cycle(
    self,
    underlying: str | None = None,
    force: bool = False,
) -> dict:
    from app.core.calendar import is_market_open
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
    now = datetime.now(IST)

    # Only run pre-market or if forced
    if not force and is_market_open(now):
        logger.info("research_cycle_skipped_market_open")
        return {"skipped": "market_open"}

    async def _run() -> dict:
        from app.agents.orchestrator import run_daily_research_cycle
        from app.core.db import AsyncSessionLocal

        watchlist = [underlying.upper()] if underlying else None

        async with AsyncSessionLocal() as db:
            return await run_daily_research_cycle(db, watchlist, force=force)

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("research_cycle_task_error")
        raise self.retry(exc=e, countdown=300)


@app.task(name="tasks.agents.run_evaluator")
def run_evaluator(days: int = 30) -> dict:
    async def _run() -> dict:
        from app.agents.evaluator import run
        from app.core.db import AsyncSessionLocal
        import uuid

        run_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            return await run(run_id, db, days=days)

    return asyncio.run(_run())
