"""Orchestrator — coordinates all agents in daily research cycle."""

import json
import uuid
from datetime import date, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import market_research, strategy, risk_assessment
from app.agents.memory import store_research
from app.agents.tools import TOOLS
from app.core.redis import get_redis
from models.agent_runs import AgentRun
from models.instruments import Instrument
from models.signals import Signal

logger = structlog.get_logger(__name__)

DEFAULT_WATCHLIST = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "HDFC", "INFOSYS", "TCS"]


async def _get_portfolio_summary(db: AsyncSession) -> dict:
    from sqlalchemy import select
    from models.paper_trades import PaperTrade
    from models.positions import Position

    open_trades_q = await db.execute(
        select(PaperTrade).where(PaperTrade.exited_at == None)  # noqa: E711
    )
    open_trades = open_trades_q.scalars().all()

    positions_q = await db.execute(
        select(Position).where(
            Position.paper_trade_id.in_([t.id for t in open_trades])
        )
    )
    positions = positions_q.scalars().all()

    return {
        "open_positions": len(open_trades),
        "capital_used": sum(t.entry_price * t.quantity for t in open_trades),
        "portfolio_delta": sum(p.delta or 0.0 for p in positions),
        "portfolio_vega": sum(p.vega or 0.0 for p in positions),
        "total_unrealized_pnl": sum(t.unrealized_pnl or 0.0 for t in open_trades),
    }


def _register_tool_handlers() -> None:
    """Wire tool definitions to real async implementations."""
    from app.agents.strategy import register_tool_handler
    from app.market_data.nse import get_nse_scraper
    from app.analytics.chain import enrich_chain
    from app.analytics.oi_analysis import compute_oi_analysis
    from app.analytics.iv_surface import build_iv_surface

    async def get_options_chain(underlying: str, expiry: str | None = None) -> dict:
        from datetime import date as date_cls
        exp = date_cls.fromisoformat(expiry) if expiry else None
        chain = await get_nse_scraper().fetch_options_chain(underlying, exp)
        if not chain:
            return {"error": "chain unavailable"}
        return {"underlying": underlying, "expiry": chain.expiry, "spot": chain.spot_price,
                "strikes": enrich_chain(chain)[:40]}

    async def get_ohlcv(symbol: str, interval: str = "1d", n_bars: int = 30) -> list:
        from app.market_data.kite import fetch_ohlcv, get_kite
        from datetime import timedelta
        to_dt = datetime.now()
        from_dt = to_dt - timedelta(days=n_bars * 2)
        # kiteconnect needs instrument token — simplified here
        return []

    async def get_oi_analysis(underlying: str, expiry: str | None = None) -> dict:
        from datetime import date as date_cls
        exp = date_cls.fromisoformat(expiry) if expiry else None
        chain = await get_nse_scraper().fetch_options_chain(underlying, exp)
        if not chain:
            return {"error": "unavailable"}
        oi = compute_oi_analysis(chain)
        return {"pcr": oi.pcr, "max_pain": oi.max_pain,
                "top_ce_strikes": oi.top_ce_strikes[:5], "top_pe_strikes": oi.top_pe_strikes[:5]}

    async def search_news(query: str, max_results: int = 10) -> list:
        from app.market_data.news import fetch_all_headlines
        headlines = await fetch_all_headlines()
        q = query.lower()
        return [h for h in headlines if q in h.get("title", "").lower()][:max_results]

    async def get_fii_dii_data(date: str | None = None) -> dict:
        return await get_nse_scraper().fetch_fii_dii() or {}

    async def get_iv_surface(underlying: str) -> dict:
        chain = await get_nse_scraper().fetch_options_chain(underlying)
        if not chain:
            return {"error": "unavailable"}
        surface = build_iv_surface([chain])
        return surface.to_dict() if surface else {}

    register_tool_handler("get_options_chain", get_options_chain)
    register_tool_handler("get_ohlcv", get_ohlcv)
    register_tool_handler("get_oi_analysis", get_oi_analysis)
    register_tool_handler("search_news", search_news)
    register_tool_handler("get_fii_dii_data", get_fii_dii_data)
    register_tool_handler("get_iv_surface", get_iv_surface)


async def run_daily_research_cycle(
    db: AsyncSession,
    watchlist: list[str] | None = None,
    force: bool = False,
) -> dict:
    _register_tool_handlers()
    watchlist = watchlist or DEFAULT_WATCHLIST
    run_id = str(uuid.uuid4())
    today = date.today().isoformat()

    # Record orchestrator run
    agent_run = AgentRun(
        id=uuid.UUID(run_id),
        agent_name="orchestrator",
        model_used="multi-agent",
        input_context={"watchlist": watchlist, "date": today},
        status="running",
    )
    db.add(agent_run)
    await db.commit()

    try:
        # Step 1: Market Research
        market_view = await market_research.run(run_id, today, watchlist)
        await store_research(
            db,
            source_type="agent_synthesis",
            summary=market_view.get("overall_market_view", ""),
            underlying=None,
            sentiment=market_view.get("sentiment"),
            structured_analysis=market_view,
            agent_run_id=run_id,
        )

        # Step 2: Strategy Agent
        recommendations = await strategy.run(run_id, market_view, watchlist)

        # Step 3: Risk Assessment per recommendation
        portfolio_summary = await _get_portfolio_summary(db)
        approved_signals = []

        for rec in recommendations:
            risk_result = await risk_assessment.run(run_id, rec, portfolio_summary)
            if risk_result.get("decision") == "approved":
                # Store signal
                from sqlalchemy import select
                instr_q = await db.execute(
                    Instrument.__table__.select().where(
                        Instrument.underlying == rec.get("underlying", "").upper()
                    )
                )
                instr = instr_q.first()
                if instr:
                    sig = Signal(
                        agent_run_id=uuid.UUID(run_id),
                        instrument_id=instr.id,
                        strategy_type=rec.get("strategy_type", "unknown"),
                        score=float(rec.get("confidence", 0.5)),
                        confidence=float(rec.get("confidence", 0.5)),
                        parameters=rec,
                        status="pending",
                    )
                    db.add(sig)
                    approved_signals.append(rec)

        await db.commit()

        # Publish signal notification
        redis = await get_redis()
        await redis.publish(
            "pubsub:signal:new",
            json.dumps({"event": "signals_generated", "count": len(approved_signals), "run_id": run_id}),
        )

        agent_run.status = "completed"
        agent_run.completed_at = datetime.now()
        agent_run.output = {"signals_generated": len(approved_signals), "market_sentiment": market_view.get("sentiment")}
        await db.commit()

        logger.info("research_cycle_complete", run_id=run_id, signals=len(approved_signals))
        return {"run_id": run_id, "signals_generated": len(approved_signals)}

    except Exception as e:
        agent_run.status = "failed"
        agent_run.error = str(e)
        await db.commit()
        logger.exception("research_cycle_error", run_id=run_id)
        raise
