"""OI build-up / unwinding detector."""

from app.market_data.normalizer import OptionsChain


def detect_oi_buildup(chain: OptionsChain, threshold_pct: float = 0.15) -> list[dict]:
    """Returns strikes where OI is >= threshold_pct of total OI — concentration signals."""
    total_ce = chain.total_ce_oi()
    total_pe = chain.total_pe_oi()
    signals = []

    for s in chain.strikes:
        ce_oi = s.ce_oi or 0
        pe_oi = s.pe_oi or 0

        if total_ce > 0 and ce_oi / total_ce >= threshold_pct:
            signals.append({
                "strike": s.strike,
                "option_type": "CE",
                "oi": ce_oi,
                "oi_pct": round(ce_oi / total_ce, 3),
                "signal": "oi_concentration",
                "interpretation": "resistance",
            })

        if total_pe > 0 and pe_oi / total_pe >= threshold_pct:
            signals.append({
                "strike": s.strike,
                "option_type": "PE",
                "oi": pe_oi,
                "oi_pct": round(pe_oi / total_pe, 3),
                "signal": "oi_concentration",
                "interpretation": "support",
            })

    return sorted(signals, key=lambda x: -x["oi_pct"])
