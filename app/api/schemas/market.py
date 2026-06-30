from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class InstrumentOut(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    instrument_type: str
    underlying: str | None
    expiry: date | None
    strike: float | None
    option_type: str | None
    lot_size: int

    model_config = {"from_attributes": True}


class QuoteOut(BaseModel):
    symbol: str
    ltp: float
    bid: float | None
    ask: float | None
    volume: int | None
    oi: int | None
    timestamp: datetime


class OHLCVBar(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int


class OptionsChainOut(BaseModel):
    underlying: str
    expiry: str
    spot_price: float
    timestamp: datetime
    strikes: list[dict]  # enriched with Greeks
    pcr: float | None
    max_pain: float | None
