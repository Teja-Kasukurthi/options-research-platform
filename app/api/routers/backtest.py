import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.backtest import BacktestRunIn, BacktestRunOut
from app.core.db import get_db
from models.backtest_runs import BacktestRun

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.post("/run", response_model=BacktestRunOut, status_code=202)
async def run_backtest(
    body: BacktestRunIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BacktestRunOut:
    run = BacktestRun(
        strategy_name=body.strategy_name,
        parameters={**body.parameters, "initial_capital": body.initial_capital},
        from_date=body.from_date,
        to_date=body.to_date,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    from tasks.backtest import run_backtest_task
    run_backtest_task.delay(str(run.id))

    return BacktestRunOut.model_validate(run)


@router.get("/runs", response_model=list[BacktestRunOut])
async def list_runs(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[BacktestRunOut]:
    result = await db.execute(
        select(BacktestRun).order_by(BacktestRun.ran_at.desc()).limit(limit)
    )
    return [BacktestRunOut.model_validate(r) for r in result.scalars().all()]


@router.get("/runs/{run_id}", response_model=BacktestRunOut)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> BacktestRunOut:
    r = await db.get(BacktestRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return BacktestRunOut.model_validate(r)


@router.get("/runs/{run_id}/trades")
async def get_run_trades(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    r = await db.get(BacktestRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {"run_id": str(run_id), "trades": r.trade_log or []}
