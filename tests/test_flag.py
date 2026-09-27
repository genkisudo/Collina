from types import SimpleNamespace

from polyflag.config import HIGH_CONFIDENCE, LOW_CONFIDENCE, REASON_MIN, WEIGHTS
from polyflag.flag import dispute_risk, to_result
from polyflag.models import Event

EVENT = Event(
    id="1", slug="will-x-cry", title="Will X cry?",
    description="Resolves Yes if X cries during the event.",
    resolution_source="", end_date="2026-10-20T23:59:00Z",
    created_at="2026-09-27T00:00:00Z", options=["Yes", "No"],
)


def _noul(v: float) -> SimpleNamespace:
    return SimpleNamespace(noul=v)


def _score(score: float, confidence: float) -> SimpleNamespace:
    return SimpleNamespace(score=score, confidence=confidence)


def _choice(choice: str, confidence: float) -> SimpleNamespace:
    return SimpleNamespace(choice=choice, confidence=confidence)


def make_response(nouls: dict[str, float], ambiguity: tuple[float, float],
                   main_risk: tuple[str, float], model: str = "jev-1.13.0") -> SimpleNamespace:
    return SimpleNamespace(
        nouls={k: _noul(v) for k, v in nouls.items()},
        scores={"ambiguity": _score(*ambiguity)},
        choices={"main_risk": _choice(*main_risk)},
        model=model,
    )


def all_nouls(value: float) -> dict[str, float]:
    return {k: value for k in WEIGHTS if k != "ambiguity"}


def test_dispute_risk_is_weighted_sum_with_normalized_ambiguity():
    nouls = {k: 1.0 for k in WEIGHTS if k != "ambiguity"}
    # ambiguity_score of 3 (top of a 4-level 0-3 scale) normalizes to 1.0
    assert dispute_risk(nouls, ambiguity_score=3.0) == 1.0
    assert dispute_risk({k: 0.0 for k in nouls}, ambiguity_score=0.0) == 0.0


def test_high_signals_flag_above_threshold():
    r = make_response(all_nouls(0.9), ambiguity=(3.0, 0.9), main_risk=("undefined_term", 0.9))
    result = to_result(EVENT, r, threshold=0.60)
    assert result.flagged
    assert result.p >= 0.60
    assert result.main_risk == "undefined_term"
    assert result.model == "jev-1.13.0"


def test_low_signals_stay_unflagged():
    r = make_response(all_nouls(0.05), ambiguity=(0.0, 0.9), main_risk=("none", 0.9))
    result = to_result(EVENT, r, threshold=0.60)
    assert not result.flagged
    assert result.p < 0.60


def test_reasons_only_include_signals_at_or_above_reason_min_sorted_desc():
    nouls = all_nouls(0.0)
    nouls["undefined_term"] = 0.95
    nouls["subjective_judgment"] = 0.55
    nouls["no_public_evidence"] = REASON_MIN - 0.01  # just below cutoff, excluded
    r = make_response(nouls, ambiguity=(1.0, 0.9), main_risk=("undefined_term", 0.9))
    result = to_result(EVENT, r, threshold=0.60)
    assert list(result.reasons.keys()) == ["undefined_term", "subjective_judgment"]
    assert result.reasons["undefined_term"] > result.reasons["subjective_judgment"]
    assert "no_public_evidence" not in result.reasons
    # every signal (not just reasons) is retained for later re-weighting
    assert result.nouls["no_public_evidence"] == REASON_MIN - 0.01


def test_main_risk_shown_only_above_high_confidence():
    r = make_response(all_nouls(0.9), ambiguity=(3.0, 0.9),
                       main_risk=("undefined_term", HIGH_CONFIDENCE - 0.01))
    result = to_result(EVENT, r, threshold=0.60)
    assert result.main_risk == "unclear"
    assert result.main_risk_confidence == HIGH_CONFIDENCE - 0.01


def test_low_confidence_threshold_matches_config():
    # sanity: report.py's "(low confidence)" note compares ambiguity_confidence to LOW_CONFIDENCE
    r = make_response(all_nouls(0.5), ambiguity=(1.5, LOW_CONFIDENCE - 0.01),
                       main_risk=("none", 0.9))
    result = to_result(EVENT, r, threshold=0.60)
    assert result.ambiguity_confidence < LOW_CONFIDENCE
