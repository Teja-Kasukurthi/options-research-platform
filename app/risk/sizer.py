"""Position sizing — fractional Kelly + fixed-fraction."""


def kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25,  # quarter-Kelly
) -> float:
    """Returns fraction of capital to risk. Capped at 2%."""
    if avg_loss == 0 or win_rate <= 0:
        return 0.0
    b = avg_win / avg_loss
    kelly = (b * win_rate - (1 - win_rate)) / b
    return max(0.0, min(0.02, kelly * fraction))


def compute_lot_size(
    capital: float,
    risk_fraction: float,
    option_price: float,
    lot_size: int,
    max_lots: int = 5,
) -> int:
    """How many lots can we buy given capital and risk fraction."""
    if option_price <= 0 or lot_size <= 0:
        return 0
    capital_at_risk = capital * risk_fraction
    cost_per_lot = option_price * lot_size
    lots = int(capital_at_risk / cost_per_lot)
    return max(0, min(lots, max_lots))
