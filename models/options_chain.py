import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OptionsChainSnapshot(Base):
    """TimescaleDB hypertable partitioned by snapshot_time. chunk_interval=4hours."""

    __tablename__ = "options_chain_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    underlying: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    expiry: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    snapshot_time: Mapped[datetime] = mapped_column(primary_key=True)
    chain_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
