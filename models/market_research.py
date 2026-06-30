import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

try:
    from pgvector.sqlalchemy import Vector
    _vector_type = Vector(1536)
except ImportError:
    from sqlalchemy import JSON as _vector_type  # type: ignore[assignment]


class MarketResearch(Base):
    __tablename__ = "market_research"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # news, fii_dii, sebi, agent_synthesis
    underlying: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    structured_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[list | None] = mapped_column(_vector_type, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # bullish, bearish, neutral
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
