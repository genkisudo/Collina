"""Convert Jev's answers into deterministic dispute scores and flags."""

from typesafe_sdk import SystemOneResponse
from .config import HIGH_CONFIDENCE, REASON_MIN, WEIGHTS
from .models import Event, Result

def dispute_risk(nouls: dict[str, float], ambiguity_score: float) -> float:
    """Weighted blend of independent signals; weights live in config.py."""
    parts = {**nouls, "ambiguity": ambiguity_score / 3}
    return sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)

def to_result(e: Event, r: SystemOneResponse, threshold: float) -> Result:
    """Score one response and retain both display reasons and raw signals."""

    nouls = {k: a.noul for k, a in r.nouls.items()}
    amb = r.scores["ambiguity"]
    risk = r.choices["main_risk"]
    p = dispute_risk(nouls, amb.score)
    reasons = dict(sorted(((k, v) for k, v in nouls.items() if v >= REASON_MIN),
                          key=lambda kv: -kv[1]))
    return Result(
        event=e, p=p, flagged=p >= threshold, reasons=reasons,
        ambiguity_score=amb.score, ambiguity_confidence=amb.confidence,
        main_risk=risk.choice if risk.confidence >= HIGH_CONFIDENCE else "unclear",
        main_risk_confidence=risk.confidence,
        nouls=nouls,
        model=r.model,
    )
