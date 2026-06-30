"""Monitor Agent — Groq Llama 3.3 70B, position health checks."""

import json
from pathlib import Path

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
PROMPT_PATH = Path(__file__).parent / "prompts" / "monitor.txt"


def _groq_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def _ollama_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key="ollama",
        base_url=f"{settings.ollama_base_url}/v1",
    )


async def run(run_id: str, positions: list[dict], market_snapshot: dict) -> list[dict]:
    if not positions:
        return []

    prompt_template = PROMPT_PATH.read_text()
    system_prompt = prompt_template.format(
        positions=json.dumps(positions, indent=2, default=str),
        market_snapshot=json.dumps(market_snapshot, indent=2, default=str),
    )

    try:
        client = _groq_client()
        model = GROQ_MODEL
    except Exception:
        client = _ollama_client()
        model = "llama3.1:8b"

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Check positions and return alerts array as JSON."},
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "[]"
        parsed = json.loads(content)
        alerts = parsed if isinstance(parsed, list) else parsed.get("alerts", [])
    except Exception:
        logger.exception("monitor_agent_error", run_id=run_id)
        alerts = []

    logger.info("monitor_agent_complete", run_id=run_id, alerts=len(alerts))
    return alerts
