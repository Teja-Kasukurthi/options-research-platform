"""Black-Scholes Greeks via py_vollib."""

from dataclasses import dataclass
from datetime import date

import structlog
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes.greeks.analytical import delta, gamma, rho, theta, vega

logger = structlog.get_logger(__name__)

RISK_FREE_RATE = 0.065  # RBI repo rate approximation


@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    iv: float
    theoretical_price: float


def compute_greeks(
    option_type: str,  # "c" or "p"
    spot: float,
    strike: float,
    expiry: date,
    iv: float,
    risk_free: float = RISK_FREE_RATE,
) -> Greeks | None:
    from datetime import date as date_cls
    today = date_cls.today()
    t = (expiry - today).days / 365.0
    if t <= 0:
        return None

    flag = option_type.lower()[0]  # "c" or "p"
    try:
        d = delta(flag, spot, strike, t, risk_free, iv)
        g = gamma(flag, spot, strike, t, risk_free, iv)
        th = theta(flag, spot, strike, t, risk_free, iv)
        v = vega(flag, spot, strike, t, risk_free, iv)
        r = rho(flag, spot, strike, t, risk_free, iv)
        price = black_scholes(flag, spot, strike, t, risk_free, iv)
        return Greeks(delta=d, gamma=g, theta=th, vega=v, rho=r, iv=iv, theoretical_price=price)
    except Exception:
        logger.debug("greeks_compute_error", flag=flag, spot=spot, strike=strike, iv=iv)
        return None


def implied_volatility(
    option_type: str,
    market_price: float,
    spot: float,
    strike: float,
    expiry: date,
    risk_free: float = RISK_FREE_RATE,
) -> float | None:
    from datetime import date as date_cls
    from py_vollib.black_scholes.implied_volatility import implied_volatility as _iv
    today = date_cls.today()
    t = (expiry - today).days / 365.0
    if t <= 0 or market_price <= 0:
        return None
    flag = option_type.lower()[0]
    try:
        return _iv(market_price, spot, strike, t, risk_free, flag)
    except Exception:
        return None
