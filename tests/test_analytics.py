import pytest
from app.analytics.greeks import compute_greeks, implied_volatility
from datetime import date, timedelta


def test_compute_greeks_call() -> None:
    expiry = date.today() + timedelta(days=30)
    g = compute_greeks("c", spot=22500, strike=22500, expiry=expiry, iv=0.15)
    assert g is not None
    assert 0 < g.delta < 1
    assert g.theta < 0
    assert g.gamma > 0
    assert g.vega > 0


def test_compute_greeks_put() -> None:
    expiry = date.today() + timedelta(days=30)
    g = compute_greeks("p", spot=22500, strike=22500, expiry=expiry, iv=0.15)
    assert g is not None
    assert -1 < g.delta < 0


def test_implied_volatility_roundtrip() -> None:
    expiry = date.today() + timedelta(days=30)
    g = compute_greeks("c", spot=22500, strike=22500, expiry=expiry, iv=0.20)
    assert g is not None
    iv = implied_volatility("c", market_price=g.price, spot=22500, strike=22500, expiry=expiry)
    assert iv is not None
    assert abs(iv - 0.20) < 0.005


def test_greeks_expired_returns_none() -> None:
    expiry = date.today() - timedelta(days=1)
    g = compute_greeks("c", spot=22500, strike=22000, expiry=expiry, iv=0.15)
    assert g is None
