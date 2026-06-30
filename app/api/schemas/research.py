from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TriggerResearchIn(BaseModel):
    underlying: str | None = None
    force: bool = False


class ResearchRunOut(BaseModel):
    id: UUID
    agent_name: str
    model_used: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    latency_ms: float | None
    output: dict | None

    model_config = {"from_attributes": True}
