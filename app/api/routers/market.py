import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_jwt
from app.api.schemas.market import InstrumentOut, OHLCVBar, OptionsChainOut, QuoteOut
from app.analytics.chain import enrich_chain
from app.analytics.oi_analysis import compute_oi_analysis
from app.core.db import get_db
from app.core.redis import get_redis
from app.market_data.kite import fetch_quote
from app.market_data.nse import get_nse_scraper
from models.instruments import Instrument
from models.ohlcv import OHLCV1Min

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/instruments", response_model=list[InstrumentOut])
async def list_instruments(
    exchange: str | None = None,
    underlying: str | None = None,
    instrument_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[InstrumentOut]:
    q = select(Instrument).where(Instrument.is_active == True)  # noqa: E712
    if exchange:
        q = q.where(Instrument.exchange == exchange.upper())
    if underlying:
        q = q.where(Instrument.underlying == underlying.upper())
    if instrument_type:
        q = q.where(Instrument.instrument_type == instrument_type.upper())
    result = await db.execute(q)
    return [InstrumentOut.model_validate(r) for r in result.scalars().all()]


@router.get("/quote/{symbol}", response_model=QuoteOut)
async def get_quote(symbol: str) -> QuoteOut:
    redis = await get_redis()
    cached = await redis.get(f"market:tick:{symbol.upper()}")
    if cached:
        data = json.loads(cached)
        return QuoteOut(
            symbol=symbol.upper(),
            ltp=data["ltp"],
            bid=data.get("bid"),
            ask=data.get("ask"),
            volume=data.get("volume"),
            oi=data.get("oi"),
            timestamp=datetime.fromisoformat(data["ts"]),
        )

    try:
        quotes = fetch_quote([f"NSE:{symbol.upper()}"])
        q = quotes.get(f"NSE:{symbol.upper()}", {})
        if not q:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return QuoteOut(
            symbol=symbol.upper(),
            ltp=q.get("last_price", 0),
            bid=q.get("depth", {}).get("buy", [{}])[0].get("price"),
            ask=q.get("depth", {}).get("sell", [{}])[0].get("price"),
            volume=q.get("volume"),
            oi=q.get("oi"),
            timestamp=datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {e}")


@router.get("/ohlcv/{symbol}", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str,
    interval: str = Query("1m", pattern="^(1m|5m|15m|1h|1d)$"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    limit: int = Query(500, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[OHLCVBar]:
    instr = await db.execute(
        select(Instrument).where(Instrument.symbol == symbol.upper(), Instrument.is_active == True)  # noqa: E712
    )
    instrument = instr.scalars().first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    q = select(OHLCV1Min).where(OHLCV1Min.instrument_id == instrument.id)
    if from_dt:
        q = q.where(OHLCV1Min.time >= from_dt)
    if to_dt:
        q = q.where(OHLCV1Min.time <= to_dt)
    q = q.order_by(OHLCV1Min.time.desc()).limit(limit)

    result = await db.execute(q)
    bars = result.scalars().all()
    return [
        OHLCVBar(time=b.time, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume, oi=b.oi)
        for b in reversed(bars)
    ]


@router.get("/options-chain/{underlying}/{expiry}", response_model=OptionsChainOut)
async def get_options_chain(underlying: str, expiry: str) -> OptionsChainOut:
    from datetime import date
    redis = await get_redis()
    cache_key = f"options:chain:{underlying.upper()}:{expiry}"
    cached = await redis.get(cache_key)
    if cached:
        return OptionsChainOut.model_validate_json(cached)

    scraper = get_nse_scraper()
    try:
        expiry_date = date.fromisoformat(expiry)
        chain = await scraper.fetch_options_chain(underlying.upper(), expiry_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiry format; use YYYY-MM-DD")

    if not chain:
        raise HTTPException(status_code=503, detail="Chain data unavailable")

    enriched = enrich_chain(chain)
    oi = compute_oi_analysis(chain)

    out = OptionsChainOut(
        underlying=chain.underlying,
        expiry=chain.expiry,
        spot_price=chain.spot_price,
        timestamp=chain.timestamp,
        strikes=enriched,
        pcr=oi.pcr,
        max_pain=oi.max_pain,
    )
    await redis.setex(cache_key, 30, out.model_dump_json())
    return out
