from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.analytics import GreeksOut, IVSurfaceOut, OIAnalysisOut
from app.analytics.greeks import compute_greeks
from app.analytics.iv_surface import build_iv_surface
from app.analytics.oi_analysis import compute_oi_analysis
from app.core.db import get_db
from app.core.redis import get_redis
from app.market_data.nse import get_nse_scraper
from models.instruments import Instrument
from models.positions import Position
from models.paper_trades import PaperTrade

import json

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/iv-surface/{underlying}", response_model=IVSurfaceOut)
async def get_iv_surface(underlying: str) -> IVSurfaceOut:
    redis = await get_redis()
    cached = await redis.get(f"analytics:iv_surface:{underlying.upper()}")
    if cached:
        return IVSurfaceOut.model_validate_json(cached)

    scraper = get_nse_scraper()
    chains = []
    for _ in range(3):  # fetch nearest 3 expiries
        chain = await scraper.fetch_options_chain(underlying.upper())
        if chain:
            chains.append(chain)
        break  # NSE API returns all expiries in one call; we parse first for now

    if not chains:
        raise HTTPException(status_code=503, detail="IV surface data unavailable")

    surface = build_iv_surface(chains)
    if not surface:
        raise HTTPException(status_code=422, detail="Not enough data for IV surface")

    out = IVSurfaceOut(**surface.to_dict())
    await redis.setex(f"analytics:iv_surface:{underlying.upper()}", 60, out.model_dump_json())
    return out


@router.get("/greeks/{instrument_id}", response_model=GreeksOut)
async def get_greeks(instrument_id: str, db: AsyncSession = Depends(get_db)) -> GreeksOut:
    from uuid import UUID
    from datetime import date
    instr = await db.get(Instrument, UUID(instrument_id))
    if not instr or instr.option_type is None:
        raise HTTPException(status_code=404, detail="Options instrument not found")

    scraper = get_nse_scraper()
    chain = await scraper.fetch_options_chain(instr.underlying or "", instr.expiry)
    if not chain:
        return GreeksOut(delta=None, gamma=None, theta=None, vega=None, iv=None, theoretical_price=None)

    for s in chain.strikes:
        if s.strike == instr.strike:
            opt_type = instr.option_type.lower()[0]
            ltp = s.ce_ltp if opt_type == "c" else s.pe_ltp
            raw_iv = s.ce_iv if opt_type == "c" else s.pe_iv
            iv = (raw_iv / 100.0) if raw_iv else None
            if ltp and instr.expiry and iv:
                g = compute_greeks(opt_type, chain.spot_price, s.strike, instr.expiry, iv)
                if g:
                    return GreeksOut(
                        delta=g.delta, gamma=g.gamma, theta=g.theta,
                        vega=g.vega, iv=iv * 100, theoretical_price=g.theoretical_price,
                    )

    return GreeksOut(delta=None, gamma=None, theta=None, vega=None, iv=None, theoretical_price=None)


@router.get("/oi-analysis/{underlying}", response_model=OIAnalysisOut)
async def get_oi_analysis(underlying: str, expiry: str | None = None) -> OIAnalysisOut:
    redis = await get_redis()
    cache_key = f"analytics:oi:{underlying.upper()}:{expiry or 'nearest'}"
    cached = await redis.get(cache_key)
    if cached:
        return OIAnalysisOut.model_validate_json(cached)

    scraper = get_nse_scraper()
    from datetime import date
    exp = date.fromisoformat(expiry) if expiry else None
    chain = await scraper.fetch_options_chain(underlying.upper(), exp)
    if not chain:
        raise HTTPException(status_code=503, detail="OI data unavailable")

    oi = compute_oi_analysis(chain)
    out = OIAnalysisOut(
        underlying=oi.underlying,
        expiry=oi.expiry,
        spot=oi.spot,
        pcr=oi.pcr,
        max_pain=oi.max_pain,
        total_ce_oi=oi.total_ce_oi,
        total_pe_oi=oi.total_pe_oi,
        top_ce_strikes=oi.top_ce_strikes,
        top_pe_strikes=oi.top_pe_strikes,
    )
    await redis.setex(cache_key, 60, out.model_dump_json())
    return out


@router.get("/pcr/{underlying}")
async def get_pcr(underlying: str, expiry: str | None = None) -> dict:
    scraper = get_nse_scraper()
    from datetime import date
    exp = date.fromisoformat(expiry) if expiry else None
    chain = await scraper.fetch_options_chain(underlying.upper(), exp)
    if not chain:
        raise HTTPException(status_code=503, detail="Data unavailable")
    return {"underlying": underlying.upper(), "pcr": chain.pcr(), "expiry": expiry}


@router.get("/max-pain/{underlying}/{expiry}")
async def get_max_pain(underlying: str, expiry: str) -> dict:
    from datetime import date
    scraper = get_nse_scraper()
    chain = await scraper.fetch_options_chain(underlying.upper(), date.fromisoformat(expiry))
    if not chain:
        raise HTTPException(status_code=503, detail="Data unavailable")
    oi = compute_oi_analysis(chain)
    return {"underlying": underlying.upper(), "expiry": expiry, "max_pain": oi.max_pain}
