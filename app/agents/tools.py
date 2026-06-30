"""Tool definitions for AI agents — Anthropic tool_use format."""

TOOLS = [
    {
        "name": "get_options_chain",
        "description": "Fetch live NSE options chain for an underlying and expiry. Returns strikes with CE/PE prices, OI, IV.",
        "input_schema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string", "description": "NSE symbol e.g. NIFTY, BANKNIFTY, RELIANCE"},
                "expiry": {"type": "string", "description": "Expiry date YYYY-MM-DD. If omitted returns nearest expiry."},
            },
            "required": ["underlying"],
        },
    },
    {
        "name": "get_ohlcv",
        "description": "Fetch historical OHLCV bars for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "interval": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "1d"], "default": "1d"},
                "n_bars": {"type": "integer", "default": 30, "description": "Number of bars to return"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_greeks",
        "description": "Compute Black-Scholes Greeks for a specific option.",
        "input_schema": {
            "type": "object",
            "properties": {
                "instrument_id": {"type": "string", "description": "UUID of the instrument"},
            },
            "required": ["instrument_id"],
        },
    },
    {
        "name": "get_oi_analysis",
        "description": "Get OI analysis including PCR, max pain, top OI strikes for an underlying.",
        "input_schema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
                "expiry": {"type": "string", "description": "YYYY-MM-DD, optional"},
            },
            "required": ["underlying"],
        },
    },
    {
        "name": "search_news",
        "description": "Search recent market news headlines for a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms e.g. 'Nifty options RBI rate'"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_fii_dii_data",
        "description": "Get FII/DII net buy/sell data for a date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD, defaults to latest available"},
            },
        },
    },
    {
        "name": "get_past_signals",
        "description": "Retrieve past trading signals with their outcomes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "approved", "rejected", "executed", "expired"]},
                "strategy_type": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
            },
        },
    },
    {
        "name": "get_position_pnl",
        "description": "Get current P&L and Greeks for an open paper trade position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "description": "UUID of the paper trade"},
            },
            "required": ["trade_id"],
        },
    },
    {
        "name": "get_iv_surface",
        "description": "Get implied volatility surface for an underlying across strikes and expiries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
            },
            "required": ["underlying"],
        },
    },
]


def openai_tool_format(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool format to OpenAI format (for Groq/Ollama)."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]
