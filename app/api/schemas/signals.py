from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SignalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    expired = "expired"


class SignalOut(BaseModel):
    id: UUID
    instrument_id: UUID
    agent_run_id: UUID | None
    generated_at: datetime
    strategy_type: str
    score: float
    confidence: float
    parameters: dict
    status: SignalStatus
    rejection_reason: str | None

    model_config = {"from_attributes": True}
