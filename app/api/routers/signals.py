import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.signals import SignalOut, SignalStatus
from app.core.db import get_db
from models.signals import Signal

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("", response_model=list[SignalOut])
async def list_signals(
    status: SignalStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[SignalOut]:
    q = select(Signal).order_by(Signal.generated_at.desc()).limit(limit)
    if status:
        q = q.where(Signal.status == status.value)
    result = await db.execute(q)
    return [SignalOut.model_validate(s) for s in result.scalars().all()]


@router.get("/{signal_id}", response_model=SignalOut)
async def get_signal(signal_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SignalOut:
    s = await db.get(Signal, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    return SignalOut.model_validate(s)


@router.post("/{signal_id}/approve", response_model=SignalOut)
async def approve_signal(signal_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SignalOut:
    s = await db.get(Signal, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    if s.status != "pending":
        raise HTTPException(status_code=409, detail=f"Signal status is {s.status}, not pending")
    s.status = "approved"
    await db.commit()
    await db.refresh(s)
    return SignalOut.model_validate(s)


@router.post("/{signal_id}/reject", response_model=SignalOut)
async def reject_signal(
    signal_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> SignalOut:
    s = await db.get(Signal, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    if s.status != "pending":
        raise HTTPException(status_code=409, detail=f"Signal status is {s.status}, not pending")
    s.status = "rejected"
    s.rejection_reason = body.get("reason", "")
    await db.commit()
    await db.refresh(s)
    return SignalOut.model_validate(s)
