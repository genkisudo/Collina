"""Model choice, filtering rules, and deterministic scoring thresholds."""

MODEL = "jev-1.13.0"
DEFAULT_THRESHOLD = 0.60
LOW_CONFIDENCE = 0.50
HIGH_CONFIDENCE = 0.70
# Weights sum to 1.0; tune these, not the questions, to change what gets flagged.
WEIGHTS = {
    "undefined_term": 0.20,
    "subjective_judgment": 0.20,
    "no_public_evidence": 0.15,
    "ambiguity": 0.15,
    "edge_case_gap": 0.10,
    "source_missing_or_vague": 0.08,
    "timing_unclear": 0.05,
    "options_not_exhaustive": 0.04,
    "title_rules_mismatch": 0.03,
}
REASON_MIN = 0.50
MAX_OPTIONS = 30
# Tag ids checked against the live API on 2026-09-27
EXCLUDE_TAG_IDS = [
    "1",       # sports
    "64",      # esports
    "21",      # crypto (covers crypto-prices, bitcoin, token sales)
    "604",     # stocks
    "101031",  # commodities
    "101757",  # recurring (5/15-min Up or Down)
    "102169",  # hide-from-new
]
# Catches price markets that carry no price tag, e.g. "output token price"
PRICE_TITLE = r"\bprices?\b|\bup or down\b"
