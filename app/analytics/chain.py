"""Options chain processor — enriches raw chain with Greeks + IV."""

from datetime import date

import structlog

from app.analytics.greeks import Greeks, compute_greeks, implied_volatility
from app.market_data.normalizer import OptionsChain, OptionStrike

logger = structlog.get_logger(__name__)


def enrich_chain(chain: OptionsChain) -> list[dict]:
    """Returns list of strike dicts with computed Greeks."""
    expiry = date.fromisoformat(chain.expiry)
    spot = chain.spot_price
    result = []

    for s in chain.strikes:
        row: dict = {"strike": s.strike}

        # CE
        if s.ce_ltp and s.ce_ltp > 0:
            iv = (s.ce_iv / 100.0) if s.ce_iv else implied_volatility("c", s.ce_ltp, spot, s.strike, expiry)
            if iv:
                g = compute_greeks("c", spot, s.strike, expiry, iv)
                row["ce"] = _greeks_to_dict(g, s.ce_ltp, s.ce_bid, s.ce_ask, s.ce_oi, s.ce_volume, iv)
            else:
                row["ce"] = _raw_dict(s.ce_ltp, s.ce_bid, s.ce_ask, s.ce_oi, s.ce_volume)
        else:
            row["ce"] = None

        # PE
        if s.pe_ltp and s.pe_ltp > 0:
            iv = (s.pe_iv / 100.0) if s.pe_iv else implied_volatility("p", s.pe_ltp, spot, s.strike, expiry)
            if iv:
                g = compute_greeks("p", spot, s.strike, expiry, iv)
                row["pe"] = _greeks_to_dict(g, s.pe_ltp, s.pe_bid, s.pe_ask, s.pe_oi, s.pe_volume, iv)
            else:
                row["pe"] = _raw_dict(s.pe_ltp, s.pe_bid, s.pe_ask, s.pe_oi, s.pe_volume)
        else:
            row["pe"] = None

        result.append(row)

    return result


def _greeks_to_dict(
    g: Greeks | None,
    ltp: float | None,
    bid: float | None,
    ask: float | None,
    oi: int | None,
    volume: int | None,
    iv: float | None,
) -> dict:
    base = _raw_dict(ltp, bid, ask, oi, volume)
    if g:
        base.update({
            "delta": round(g.delta, 4),
            "gamma": round(g.gamma, 6),
            "theta": round(g.theta, 2),
            "vega": round(g.vega, 4),
            "iv": round((iv or 0) * 100, 2),
            "theoretical": round(g.theoretical_price, 2),
        })
    return base


def _raw_dict(
    ltp: float | None,
    bid: float | None,
    ask: float | None,
    oi: int | None,
    volume: int | None,
) -> dict:
    return {"ltp": ltp, "bid": bid, "ask": ask, "oi": oi, "volume": volume}
