"""Validated event and scoring records shared across the pipeline."""

from datetime import datetime
from pydantic import BaseModel

class Event(BaseModel):
    """An open Polymarket event and the options sent to Jev."""

    id: str
    slug: str
    title: str
    description: str
    resolution_source: str
    end_date: str | None
    created_at: datetime
    options: list[str]

class Result(BaseModel):
    """A scored event, including raw signals for later reweighting."""

    event: Event
    p: float
    flagged: bool
    ambiguity_score: float
    ambiguity_confidence: float
    main_risk: str
    main_risk_confidence: float
    reasons: dict[str, float]    # signals at or above REASON_MIN
    nouls: dict[str, float]      # every signal, for tuning
    model: str                   # versioned model id that answered
