"""OI analysis — PCR, max pain, OI concentration."""

from dataclasses import dataclass

from app.market_data.normalizer import OptionsChain


@dataclass
class OIAnalysis:
    underlying: str
    expiry: str
    spot: float
    pcr: float | None
    max_pain: float | None
    total_ce_oi: int
    total_pe_oi: int
    top_ce_strikes: list[dict]  # [{strike, oi}] sorted desc
    top_pe_strikes: list[dict]
    ce_unwinding_strikes: list[float]
    pe_buildup_strikes: list[float]


def compute_oi_analysis(chain: OptionsChain) -> OIAnalysis:
    ce_oi = [(s.strike, s.ce_oi or 0) for s in chain.strikes]
    pe_oi = [(s.strike, s.pe_oi or 0) for s in chain.strikes]

    total_ce = sum(v for _, v in ce_oi)
    total_pe = sum(v for _, v in pe_oi)
    pcr = total_pe / total_ce if total_ce > 0 else None

    max_pain = _compute_max_pain(chain)

    top_ce = sorted([{"strike": k, "oi": v} for k, v in ce_oi], key=lambda x: -x["oi"])[:5]
    top_pe = sorted([{"strike": k, "oi": v} for k, v in pe_oi], key=lambda x: -x["oi"])[:5]

    return OIAnalysis(
        underlying=chain.underlying,
        expiry=chain.expiry,
        spot=chain.spot_price,
        pcr=pcr,
        max_pain=max_pain,
        total_ce_oi=total_ce,
        total_pe_oi=total_pe,
        top_ce_strikes=top_ce,
        top_pe_strikes=top_pe,
        ce_unwinding_strikes=[],
        pe_buildup_strikes=[],
    )


def _compute_max_pain(chain: OptionsChain) -> float | None:
    """Max pain = strike where total option buyer loss is maximum."""
    if not chain.strikes:
        return None

    strikes = [s.strike for s in chain.strikes]
    min_loss = float("inf")
    max_pain_strike = strikes[0]

    for test_strike in strikes:
        total_loss = 0.0
        for s in chain.strikes:
            ce_oi = s.ce_oi or 0
            pe_oi = s.pe_oi or 0
            # CE buyer loss if expires below test_strike
            if test_strike < s.strike:
                total_loss += ce_oi * (s.strike - test_strike)
            # PE buyer loss if expires above test_strike
            if test_strike > s.strike:
                total_loss += pe_oi * (test_strike - s.strike)

        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = test_strike

    return max_pain_strike
