from pydantic import BaseModel


class GreeksOut(BaseModel):
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    iv: float | None
    theoretical_price: float | None


class IVSurfaceOut(BaseModel):
    underlying: str
    spot: float
    strikes: list[float]
    expiries: list[str]
    iv_matrix: list[list[float | None]]


class OIAnalysisOut(BaseModel):
    underlying: str
    expiry: str
    spot: float
    pcr: float | None
    max_pain: float | None
    total_ce_oi: int
    total_pe_oi: int
    top_ce_strikes: list[dict]
    top_pe_strikes: list[dict]
