"""Implied volatility surface construction."""

from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy.interpolate import RectBivariateSpline

from app.analytics.greeks import implied_volatility
from app.market_data.normalizer import OptionsChain


@dataclass
class IVSurface:
    underlying: str
    spot: float
    strikes: list[float]
    expiries: list[str]  # YYYY-MM-DD
    iv_matrix: list[list[float | None]]  # [expiry_idx][strike_idx]

    def to_dict(self) -> dict:
        return {
            "underlying": self.underlying,
            "spot": self.spot,
            "strikes": self.strikes,
            "expiries": self.expiries,
            "iv_matrix": self.iv_matrix,
        }


def build_iv_surface(chains: list[OptionsChain]) -> IVSurface | None:
    if not chains:
        return None

    underlying = chains[0].underlying
    spot = chains[0].spot_price

    all_strikes: set[float] = set()
    for chain in chains:
        for s in chain.strikes:
            all_strikes.add(s.strike)
    strikes = sorted(all_strikes)
    expiries = [c.expiry for c in chains]

    iv_matrix: list[list[float | None]] = []
    for chain in chains:
        expiry = date.fromisoformat(chain.expiry)
        strike_to_iv: dict[float, float] = {}
        for s in chain.strikes:
            # prefer CE IV, fall back to PE
            iv = s.ce_iv
            if not iv and s.ce_ltp and s.ce_ltp > 0:
                iv = implied_volatility("c", s.ce_ltp, spot, s.strike, expiry)
            if iv and iv > 0:
                strike_to_iv[s.strike] = iv / 100.0  # NSE gives percentage

        row = [strike_to_iv.get(k) for k in strikes]
        iv_matrix.append(row)

    return IVSurface(
        underlying=underlying,
        spot=spot,
        strikes=strikes,
        expiries=expiries,
        iv_matrix=iv_matrix,
    )


def interpolate_iv(surface: IVSurface, strike: float, expiry_str: str) -> float | None:
    """Bivariate spline interpolation for a specific strike/expiry."""
    try:
        expiry_idx = surface.expiries.index(expiry_str)
    except ValueError:
        return None

    row = surface.iv_matrix[expiry_idx]
    known = [(s, v) for s, v in zip(surface.strikes, row) if v is not None]
    if len(known) < 2:
        return None

    ks, ivs = zip(*known)
    return float(np.interp(strike, ks, ivs))
