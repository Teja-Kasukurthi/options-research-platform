import pytest
from app.risk.gates import layer1_portfolio_checks, layer2_position_sizing, layer3_trade_params
from app.risk.sizer import kelly_position_size


def test_layer1_pass() -> None:
    result = layer1_portfolio_checks(
        open_positions=2,
        sector_concentration=0.2,
        net_delta=10_000,
        capital_utilization=0.5,
    )
    assert result.passed


def test_layer1_too_many_positions() -> None:
    result = layer1_portfolio_checks(
        open_positions=6,
        sector_concentration=0.2,
        net_delta=10_000,
        capital_utilization=0.5,
    )
    assert not result.passed
    assert "position" in result.reason.lower()


def test_layer1_sector_breach() -> None:
    result = layer1_portfolio_checks(
        open_positions=2,
        sector_concentration=0.5,
        net_delta=10_000,
        capital_utilization=0.5,
    )
    assert not result.passed


def test_layer2_pass() -> None:
    result = layer2_position_sizing(trade_capital_pct=0.015, var_pct=0.03)
    assert result.passed


def test_layer2_trade_too_large() -> None:
    result = layer2_position_sizing(trade_capital_pct=0.05, var_pct=0.03)
    assert not result.passed


def test_layer3_pass() -> None:
    result = layer3_trade_params(
        stop_loss=100.0,
        rr_ratio=2.0,
        days_to_expiry=15,
        bid_ask_spread_pct=1.0,
    )
    assert result.passed


def test_layer3_no_stop_loss() -> None:
    result = layer3_trade_params(
        stop_loss=None,
        rr_ratio=2.0,
        days_to_expiry=15,
        bid_ask_spread_pct=1.0,
    )
    assert not result.passed


def test_kelly_sizing() -> None:
    size = kelly_position_size(
        win_prob=0.55,
        win_pct=0.3,
        loss_pct=0.15,
        capital=500_000,
        fraction=0.25,
    )
    assert size > 0
    assert size < 500_000
