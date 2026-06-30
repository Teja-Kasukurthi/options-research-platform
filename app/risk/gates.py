"""Pre-trade risk gate layers."""

from dataclasses import dataclass


@dataclass
class GateResult:
    passed: bool
    failed_rule: str | None
    message: str


def layer1_portfolio_checks(
    open_positions: int,
    sector_concentration: float,
    net_delta: float,
    capital_utilization: float,
) -> GateResult:
    if open_positions >= 5:
        return GateResult(False, "max_positions", f"Already {open_positions} open positions (max 5)")
    if sector_concentration > 0.40:
        return GateResult(False, "sector_concentration", f"Sector concentration {sector_concentration:.0%} > 40%")
    if abs(net_delta) > 50_000:
        return GateResult(False, "delta_breach", f"Net delta Rs{net_delta:,.0f} exceeds Rs50,000 limit")
    if capital_utilization > 0.80:
        return GateResult(False, "capital_utilization", f"Capital utilization {capital_utilization:.0%} > 80%")
    return GateResult(True, None, "Layer 1 passed")


def layer2_position_sizing(
    trade_capital_pct: float,
    var_pct: float,
) -> GateResult:
    if trade_capital_pct > 0.02:
        return GateResult(False, "max_trade_size", f"Trade size {trade_capital_pct:.1%} exceeds 2% limit")
    if var_pct > 0.05:
        return GateResult(False, "var_breach", f"1-day VaR {var_pct:.1%} exceeds 5% limit")
    return GateResult(True, None, "Layer 2 passed")


def layer3_trade_params(
    stop_loss: float | None,
    rr_ratio: float | None,
    days_to_expiry: int,
    bid_ask_spread_pct: float,
) -> GateResult:
    if stop_loss is None:
        return GateResult(False, "no_stop_loss", "Stop-loss must be defined")
    if rr_ratio is None or rr_ratio < 1.5:
        return GateResult(False, "rr_ratio", f"R:R ratio {rr_ratio} < 1.5 minimum")
    if days_to_expiry < 7:
        return GateResult(False, "expiry_too_close", f"Expiry in {days_to_expiry} days (< 7 days)")
    if bid_ask_spread_pct > 0.02:
        return GateResult(False, "spread_too_wide", f"Bid-ask spread {bid_ask_spread_pct:.1%} > 2%")
    return GateResult(True, None, "Layer 3 passed")


def run_all_gates(
    open_positions: int,
    net_delta: float,
    capital_utilization: float,
    trade_capital_pct: float,
    var_pct: float,
    stop_loss: float | None,
    rr_ratio: float | None,
    days_to_expiry: int,
    bid_ask_spread_pct: float,
    sector_concentration: float = 0.0,
) -> list[GateResult]:
    results = [
        layer1_portfolio_checks(open_positions, sector_concentration, net_delta, capital_utilization),
        layer2_position_sizing(trade_capital_pct, var_pct),
        layer3_trade_params(stop_loss, rr_ratio, days_to_expiry, bid_ask_spread_pct),
    ]
    return results
