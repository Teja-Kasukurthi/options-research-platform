"""Historical simulation VaR for options portfolio."""

import numpy as np


def historical_var(
    pnl_series: list[float],
    confidence: float = 0.99,
    portfolio_value: float = 500_000.0,
) -> float:
    """
    Returns 1-day VaR as a fraction of portfolio_value.
    pnl_series: list of daily P&L values (positive = profit).
    """
    if len(pnl_series) < 10:
        return 0.0
    arr = np.array(pnl_series)
    var_abs = -np.percentile(arr, (1 - confidence) * 100)
    return var_abs / portfolio_value if portfolio_value > 0 else 0.0


def parametric_var(
    portfolio_delta: float,
    spot: float,
    daily_vol: float = 0.01,  # 1% daily move for Nifty
    confidence: float = 0.99,
) -> float:
    """Simple delta-approximation VaR."""
    from scipy.stats import norm
    z = norm.ppf(confidence)
    return abs(portfolio_delta * spot * daily_vol * z)
