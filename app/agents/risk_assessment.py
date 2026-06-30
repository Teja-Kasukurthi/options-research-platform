"""Risk Assessment Agent — Claude Haiku 4.5, structured output."""

import json
import time
from pathlib import Path

import anthropic
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"
PROMPT_PATH = Path(__file__).parent / "prompts" / "risk_assessment.txt"


async def run(
    run_id: str,
    trade_proposal: dict,
    portfolio_summary: dict,
) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt_template = PROMPT_PATH.read_text()
    system_prompt = prompt_template.format(
        portfolio_summary=json.dumps(portfolio_summary, indent=2),
        trade_proposal=json.dumps(trade_proposal, indent=2),
    )

    t0 = time.time()
    resp = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "Evaluate this trade proposal against risk rules. Output JSON only."}
        ],
    )

    tokens_in = resp.usage.input_tokens
    tokens_out = resp.usage.output_tokens
    latency_ms = (time.time() - t0) * 1000
    cost_usd = (tokens_in * 0.8 + tokens_out * 4.0) / 1_000_000  # Haiku pricing

    content = ""
    for block in resp.content:
        if hasattr(block, "text"):
            content = block.text
            break

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"decision": "rejected", "reason": "Risk agent parse error"}

    logger.info(
        "risk_assessment_complete",
        run_id=run_id,
        decision=result.get("decision"),
        cost_usd=round(cost_usd, 5),
        latency_ms=round(latency_ms),
    )
    return result
