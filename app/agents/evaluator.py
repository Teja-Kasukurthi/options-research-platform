"""Evaluator Agent — Claude Sonnet 4.6, self-improvement loop."""

import json
import time
from datetime import date, timedelta
from pathlib import Path

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from models.paper_trades import PaperTrade
from models.signals import Signal

logger = structlog.get_logger(__name__)

MODEL = "claude-sonnet-4-6"
PROMPT_PATH = Path(__file__).parent / "prompts" / "evaluator.txt"


async def _gather_signals_with_outcomes(db: AsyncSession, days: int = 30) -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Signal).where(Signal.generated_at >= cutoff).order_by(Signal.generated_at.desc())
    )
    signals = result.scalars().all()

    rows = []
    for sig in signals:
        trade_q = await db.execute(
            select(PaperTrade).where(PaperTrade.signal_id == sig.id)
        )
        trade = trade_q.scalars().first()
        rows.append({
            "signal_id": str(sig.id),
            "strategy_type": sig.strategy_type,
            "confidence": sig.confidence,
            "score": sig.score,
            "status": sig.status,
            "generated_at": sig.generated_at.isoformat(),
            "realized_pnl": trade.realized_pnl if trade else None,
            "exit_reason": trade.exit_reason if trade else None,
        })
    return rows


async def run(run_id: str, db: AsyncSession, days: int = 30) -> dict:
    signals_data = await _gather_signals_with_outcomes(db, days)

    if not signals_data:
        return {"summary": {"total_signals": 0}, "improvement_notes": []}

    prompt_template = PROMPT_PATH.read_text()
    today = date.today()
    system_prompt = prompt_template.format(
        date_range=f"{(today - timedelta(days=days)).isoformat()} to {today.isoformat()}",
        signals_data=json.dumps(signals_data[:50], indent=2),  # cap context
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    t0 = time.time()

    resp = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": "Analyze and output evaluation JSON."}],
    )

    tokens_in = resp.usage.input_tokens
    tokens_out = resp.usage.output_tokens
    latency_ms = (time.time() - t0) * 1000
    cost_usd = (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000

    content = ""
    for block in resp.content:
        if hasattr(block, "text"):
            content = block.text
            break

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"error": "parse_error"}

    logger.info(
        "evaluator_complete",
        run_id=run_id,
        signals_analyzed=len(signals_data),
        cost_usd=round(cost_usd, 4),
        latency_ms=round(latency_ms),
    )
    return result
