"""Strategy Agent — Claude Sonnet 4.6 with tool use."""

import json
import time
from datetime import datetime
from pathlib import Path

import anthropic
import structlog

from app.agents.tools import TOOLS
from app.core.config import settings

logger = structlog.get_logger(__name__)

MODEL = "claude-sonnet-4-6"
PROMPT_PATH = Path(__file__).parent / "prompts" / "strategy.txt"

_TOOL_HANDLERS: dict = {}  # populated by orchestrator


def register_tool_handler(name: str, fn) -> None:  # type: ignore[type-arg]
    _TOOL_HANDLERS[name] = fn


async def _execute_tool(name: str, inputs: dict) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = await handler(**inputs)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def run(run_id: str, market_view: dict, watchlist: list[str]) -> list[dict]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt_template = PROMPT_PATH.read_text()
    system_prompt = prompt_template.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        market_view=json.dumps(market_view, indent=2),
        watchlist=", ".join(watchlist),
    )

    messages = [
        {"role": "user", "content": f"Analyze these underlyings: {', '.join(watchlist)}. Fetch data using tools and generate trade recommendations."}
    ]

    t0 = time.time()
    tokens_in = tokens_out = 0
    recommendations: list[dict] = []

    # Agentic loop — max 10 turns
    for _ in range(10):
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        tokens_in += resp.usage.input_tokens
        tokens_out += resp.usage.output_tokens

        if resp.stop_reason == "end_turn":
            for block in resp.content:
                if hasattr(block, "text"):
                    try:
                        recommendations = json.loads(block.text)
                    except json.JSONDecodeError:
                        pass
            break

        if resp.stop_reason == "tool_use":
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = await _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    latency_ms = (time.time() - t0) * 1000
    cost_usd = (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000  # Sonnet pricing

    logger.info(
        "strategy_agent_complete",
        run_id=run_id,
        recommendations=len(recommendations),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=round(cost_usd, 4),
        latency_ms=round(latency_ms),
    )

    return recommendations if isinstance(recommendations, list) else []
