"""IV spike detector — signals elevated premium / event risk."""

from app.market_data.normalizer import OptionsChain


def detect_iv_spike(
    chain: OptionsChain,
    spike_threshold_pct: float = 0.25,  # 25% above ATM IV
) -> list[dict]:
    """Find strikes where IV is significantly above ATM IV."""
    atm = chain.atm_strike
    atm_strike = next((s for s in chain.strikes if s.strike == atm), None)
    if not atm_strike:
        return []

    atm_iv = atm_strike.ce_iv or atm_strike.pe_iv
    if not atm_iv:
        return []

    spikes = []
    for s in chain.strikes:
        for opt, raw_iv in [("CE", s.ce_iv), ("PE", s.pe_iv)]:
            if raw_iv and raw_iv > atm_iv * (1 + spike_threshold_pct):
                spikes.append({
                    "strike": s.strike,
                    "option_type": opt,
                    "iv": raw_iv,
                    "atm_iv": atm_iv,
                    "spike_pct": round((raw_iv - atm_iv) / atm_iv, 3),
                    "signal": "iv_spike",
                })
    return sorted(spikes, key=lambda x: -x["spike_pct"])
