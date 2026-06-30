import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.research import ResearchRunOut, TriggerResearchIn
from app.core.db import get_db
from models.agent_runs import AgentRun
from models.market_research import MarketResearch

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.post("/trigger", status_code=202)
async def trigger_research(body: TriggerResearchIn) -> dict:
    from tasks.agents import run_research_cycle
    task = run_research_cycle.delay(underlying=body.underlying, force=body.force)
    return {"task_id": task.id, "status": "queued"}


@router.get("/runs", response_model=list[ResearchRunOut])
async def list_runs(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[ResearchRunOut]:
    result = await db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    )
    return [ResearchRunOut.model_validate(r) for r in result.scalars().all()]


@router.get("/runs/{run_id}", response_model=ResearchRunOut)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ResearchRunOut:
    r = await db.get(AgentRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return ResearchRunOut.model_validate(r)


@router.get("/insights/{underlying}")
async def get_insights(
    underlying: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(MarketResearch)
        .where(MarketResearch.underlying == underlying.upper())
        .order_by(MarketResearch.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "created_at": r.created_at.isoformat(),
            "source_type": r.source_type,
            "summary": r.summary,
            "sentiment": r.sentiment,
            "structured_analysis": r.structured_analysis,
        }
        for r in rows
    ]
