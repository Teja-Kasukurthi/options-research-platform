"""Composite signal scorer — combines OI, IV, technicals, AI confidence."""

from dataclasses import dataclass


@dataclass
class SignalScore:
    total: float  # 0.0 – 1.0
    oi_score: float
    iv_score: float
    technical_score: float
    ai_confidence: float
    rationale: str


def compute_score(
    oi_concentration: list[dict],
    iv_spikes: list[dict],
    pcr: float | None,
    ai_confidence: float,
    rr_ratio: float,
) -> SignalScore:
    # OI score: high concentration near target strike
    oi_score = min(1.0, sum(s["oi_pct"] for s in oi_concentration[:3]) * 2)

    # IV score: moderate IV = good (premium). Too high = expensive entry.
    iv_score = 0.5
    if iv_spikes:
        avg_spike = sum(s["spike_pct"] for s in iv_spikes) / len(iv_spikes)
        iv_score = max(0.0, 1.0 - avg_spike)  # spike hurts score

    # Technical score: PCR signals
    if pcr is None:
        technical_score = 0.5
    elif 0.7 <= pcr <= 1.3:
        technical_score = 0.7  # neutral/balanced
    elif pcr > 1.3:
        technical_score = 0.8  # heavy PE OI = bullish for CE
    else:
        technical_score = 0.4  # light PE OI = bearish

    # R:R bonus
    rr_bonus = min(0.2, (rr_ratio - 1.5) * 0.1) if rr_ratio >= 1.5 else 0.0

    total = (
        oi_score * 0.25
        + iv_score * 0.20
        + technical_score * 0.20
        + ai_confidence * 0.35
        + rr_bonus
    )
    total = round(min(1.0, max(0.0, total)), 3)

    return SignalScore(
        total=total,
        oi_score=round(oi_score, 3),
        iv_score=round(iv_score, 3),
        technical_score=round(technical_score, 3),
        ai_confidence=round(ai_confidence, 3),
        rationale=f"OI:{oi_score:.2f} IV:{iv_score:.2f} Tech:{technical_score:.2f} AI:{ai_confidence:.2f}",
    )
