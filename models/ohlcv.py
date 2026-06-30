import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OHLCV1Min(Base):
    """TimescaleDB hypertable partitioned by time. chunk_interval=1day."""

    __tablename__ = "ohlcv_1min"
    __table_args__ = (
        Index("ix_ohlcv_instrument_time", "instrument_id", "time"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id"), primary_key=True
    )
    time: Mapped[datetime] = mapped_column(primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    oi: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
