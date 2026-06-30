import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(10), nullable=False)  # EQ, FUT, CE, PE
    underlying: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    expiry: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(2), nullable=True)  # CE, PE
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    kite_instrument_token: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
