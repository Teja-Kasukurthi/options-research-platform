"""Celery tasks — backtesting."""

import asyncio

import structlog

from tasks import app

logger = structlog.get_logger(__name__)


@app.task(name="tasks.backtest.run_backtest_task", bind=True, max_retries=1)
def run_backtest_task(self, run_id: str) -> dict:
    async def _run() -> dict:
        from app.backtester.engine import BacktestEngine
        from app.core.db import AsyncSessionLocal
        from models.backtest_runs import BacktestRun
        from datetime import datetime
        import uuid

        async with AsyncSessionLocal() as db:
            run = await db.get(BacktestRun, uuid.UUID(run_id))
            if not run:
                return {"error": "run not found"}

            run.status = "running"
            await db.commit()

            try:
                engine = BacktestEngine(db)
                metrics = await engine.run(
                    strategy_name=run.strategy_name,
                    parameters=run.parameters,
                    from_date=run.from_date,
                    to_date=run.to_date,
                )

                run.status = "completed"
                run.completed_at = datetime.now()
                run.total_return = metrics.get("total_return")
                run.sharpe_ratio = metrics.get("sharpe_ratio")
                run.sortino_ratio = metrics.get("sortino_ratio")
                run.max_drawdown = metrics.get("max_drawdown")
                run.win_rate = metrics.get("win_rate")
                run.total_trades = metrics.get("total_trades")
                run.full_metrics = metrics
                run.equity_curve = metrics.get("equity_curve", [])
                run.trade_log = metrics.get("trades", [])

                await db.commit()
                logger.info("backtest_complete", run_id=run_id, trades=run.total_trades)
                return {"run_id": run_id, "status": "completed", "trades": run.total_trades}

            except Exception as e:
                run.status = "failed"
                await db.commit()
                logger.exception("backtest_failed", run_id=run_id)
                raise

    return asyncio.run(_run())
