"""Greeks-decomposed P&L computation for open positions."""

from datetime import date

from app.analytics.greeks import compute_greeks, implied_volatility


def compute_unrealized_pnl(
    action: str,  # BUY or SELL
    entry_price: float,
    current_price: float,
    quantity: int,
) -> float:
    multiplier = 1 if action == "BUY" else -1
    return multiplier * (current_price - entry_price) * quantity


def compute_position_greeks(
    option_type: str,
    spot: float,
    strike: float,
    expiry: date,
    ltp: float,
    quantity: int,
    lot_size: int,
) -> dict:
    iv = implied_volatility(option_type, ltp, spot, strike, expiry)
    if not iv:
        return {}
    g = compute_greeks(option_type, spot, strike, expiry, iv)
    if not g:
        return {}
    lots = quantity // lot_size
    return {
        "delta": round(g.delta * lots * lot_size, 4),
        "gamma": round(g.gamma * lots * lot_size, 6),
        "theta": round(g.theta * lots * lot_size, 2),
        "vega": round(g.vega * lots * lot_size, 4),
        "iv": round(iv * 100, 2),
    }
