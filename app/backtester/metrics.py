"""Backtest performance metrics."""

import math
from typing import Sequence


def sharpe_ratio(daily_returns: Sequence[float], risk_free_daily: float = 0.065 / 252) -> float:
    if len(daily_returns) < 2:
        return 0.0
    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean - risk_free_daily) / std * math.sqrt(252)


def sortino_ratio(daily_returns: Sequence[float], risk_free_daily: float = 0.065 / 252) -> float:
    if len(daily_returns) < 2:
        return 0.0
    mean = sum(daily_returns) / len(daily_returns)
    downside = [min(0.0, r - risk_free_daily) for r in daily_returns]
    downside_variance = sum(d ** 2 for d in downside) / len(downside)
    downside_std = math.sqrt(downside_variance)
    if downside_std == 0:
        return 0.0
    return (mean - risk_free_daily) / downside_std * math.sqrt(252)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def win_rate(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    winners = sum(1 for t in trades if (t.get("pnl") or 0) > 0)
    return winners / len(trades)


def compute_all_metrics(
    trades: list[dict],
    equity_curve: list[float],
    initial_capital: float,
) -> dict:
    if not equity_curve:
        return {}

    final = equity_curve[-1]
    total_return = (final - initial_capital) / initial_capital if initial_capital > 0 else 0.0

    daily_returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] > 0
    ]

    return {
        "total_return": round(total_return, 4),
        "sharpe_ratio": round(sharpe_ratio(daily_returns), 3),
        "sortino_ratio": round(sortino_ratio(daily_returns), 3),
        "max_drawdown": round(max_drawdown(equity_curve), 4),
        "win_rate": round(win_rate(trades), 4),
        "total_trades": len(trades),
        "final_capital": round(final, 2),
    }
