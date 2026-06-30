"""Signal filters — liquidity and statistical gates."""

from app.market_data.normalizer import OptionsChain, OptionStrike


def passes_liquidity_filter(
    strike: OptionStrike,
    option_type: str,  # "CE" or "PE"
    min_oi: int = 200,
    max_spread_pct: float = 0.03,
) -> bool:
    if option_type == "CE":
        oi = strike.ce_oi or 0
        bid = strike.ce_bid or 0
        ask = strike.ce_ask or 0
    else:
        oi = strike.pe_oi or 0
        bid = strike.pe_bid or 0
        ask = strike.pe_ask or 0

    if oi < min_oi:
        return False
    if ask <= 0:
        return False
    spread_pct = (ask - bid) / ask if ask > 0 else 1.0
    return spread_pct <= max_spread_pct


def passes_expiry_filter(expiry_str: str, min_days: int = 7) -> bool:
    from datetime import date
    try:
        exp = date.fromisoformat(expiry_str)
        return (exp - date.today()).days >= min_days
    except ValueError:
        return False
