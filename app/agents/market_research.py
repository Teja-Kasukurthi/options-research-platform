"""Market Research Agent — Groq Llama 3.3 70B (free tier)."""

import json
from datetime import datetime
from pathlib import Path

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.memory import store_short_term
from app.core.config import settings
from app.market_data.news import fetch_all_headlines
from app.market_data.nse import get_nse_scraper

logger = structlog.get_logger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
PROMPT_PATH = Path(__file__).parent / "prompts" / "market_research.txt"


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


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=3, max=10))
async def run(
    run_id: str,
    date: str,
    watchlist: list[str],
) -> dict:
    headlines = await fetch_all_headlines()
    fii_dii = await get_nse_scraper().fetch_fii_dii()

    prompt_template = PROMPT_PATH.read_text()
    system_prompt = prompt_template.format(date=date, watchlist=", ".join(watchlist))

    context = (
        f"NEWS HEADLINES:\n"
        + "\n".join(f"- {h['source']}: {h['title']}" for h in headlines[:30])
        + f"\n\nFII/DII DATA:\n{json.dumps(fii_dii, indent=2)}"
    )

    try:
        client = _groq_client()
        model = GROQ_MODEL
    except Exception:
        client = _ollama_client()
        model = "qwen2.5:14b"

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        result = json.loads(content)
    except Exception:
        logger.exception("market_research_llm_error", model=model)
        result = {"error": "LLM unavailable", "sentiment": "neutral"}

    await store_short_term(run_id, "market_view", result)
    logger.info("market_research_complete", run_id=run_id, sentiment=result.get("sentiment"))
    return result
