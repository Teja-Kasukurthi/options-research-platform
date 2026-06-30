"""Slippage model and fill price computation."""


def compute_fill_price(
    bid: float,
    ask: float,
    oi: int,
    action: str,  # BUY or SELL
) -> tuple[float, str]:
    """
    Returns (fill_price, liquidity_tier).
    Architecture §13 slippage model.
    """
    if ask <= 0:
        return bid, "unknown"

    spread_pct = (ask - bid) / ask if ask > 0 else 1.0

    if oi > 1000 and spread_pct < 0.01:
        tier = "liquid"
        fill = (bid + ask) / 2 + (ask - bid) * 0.5 if action == "BUY" else (bid + ask) / 2 - (ask - bid) * 0.5
    elif oi > 200 and spread_pct <= 0.02:
        tier = "semi_liquid"
        fill = ask if action == "BUY" else bid
    else:
        tier = "illiquid"
        fill = ask * 1.005 if action == "BUY" else bid * 0.995

    return round(fill, 2), tier
