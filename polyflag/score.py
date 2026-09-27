"""Define atomic Jev questions and submit one batch per event."""

from typesafe_sdk import Choice, Noul, NoulCriteria, Score, SystemOneResponse, TypeSafeClient
from .config import MAX_OPTIONS, MODEL
from .models import Event

def _noul(question: str, inspect: str, focus: str, yes: dict, no: dict) -> Noul:
    """Build a yes/no question with explicit positive and negative criteria."""

    return Noul(
        instructions={"question": question, "inspect": inspect, "focus": focus},
        criteria=NoulCriteria(true=yes, false=no),
    )

QUESTIONS = {
    # --- Detection: one property each, all over the same state, run in parallel.
    "undefined_term": _noul(
        "Does the outcome depend on a word `rules` does not define?",
        "`rules`",
        "Look for a word two readers could apply differently to the same footage or report.",
        {"what": "A deciding word is left to the reader",
         "examples": ["'cry' with no definition of visible tears",
                      "'a suit' with no definition of jacket and tie"]},
        {"what": "Every deciding word is defined or has one common meaning",
         "not_for": "A vague word that does not affect which side wins",
         "examples": ["'wins the election' with a named certifying body"]},
    ),
    "subjective_judgment": _noul(
        "Does resolving `rules` require someone's judgment rather than a checkable fact?",
        "`rules`",
        "Judge the act of resolving, not how hard the outcome is to predict.",
        {"what": "A person must form an opinion to pick a side",
         "examples": ["Whether a speech 'praised' someone",
                      "Whether a performance was 'a flop'"]},
        {"what": "A named record, vote count or official statement settles it",
         "examples": ["Whether the Fed announced a 25 bps cut"]},
    ),
    "no_public_evidence": _noul(
        "Could the outcome in `rules` occur without clear public evidence that it did?",
        "`rules`",
        "Ask whether the event would reliably be recorded somewhere anyone can check.",
        {"what": "The event can happen unobserved or only on unreliable footage",
         "examples": ["A private remark", "A brief expression not on camera"]},
        {"what": "Any qualifying event is published by default",
         "examples": ["An SEC filing", "A certified election result"]},
    ),
    "source_missing_or_vague": _noul(
        "Is `resolution_source` missing or too vague to settle a close call?",
        "`resolution_source` and `rules`",
        "A source named only inside `rules` still counts as named.",
        {"what": "No source, or several with no tie-break",
         "examples": ["Empty source and none named in the rules",
                      "'credible media reports'"]},
        {"what": "One named source, or a clear order of precedence",
         "examples": ["A named agency's official page"]},
    ),
    "timing_unclear": _noul(
        "Is the deadline, time zone or window in `rules` ambiguous?",
        "`rules`",
        "Judge the wording only; do not compare dates. "
        "Check that a reader could tell whether an event on the last day counts.",
        {"what": "No time zone, or a cut-off described in words two readers could place differently",
         "examples": ["'by October 30' with no time or zone",
                      "'before the end of the month' with no month named"]},
        {"what": "An explicit date, time and zone",
         "examples": ["11:59 PM ET on October 20, 2026"]},
    ),
    "edge_case_gap": _noul(
        "Is there a plausible event `rules` does not say how to resolve?",
        "`rules`",
        "Consider postponement, cancellation, a tie, a partial result, or a withdrawal.",
        {"what": "A likely scenario has no stated outcome",
         "examples": ["A match postponed past the end date, with no rule for it"]},
        {"what": "The rules name a fallback for delays and non-events",
         "examples": ["'If the event is cancelled, this resolves No'"]},
    ),
    "options_not_exhaustive": _noul(
        "Could the real outcome fall outside every entry in `options`?",
        "`options` and `rules`",
        "Only for multi-option events; a Yes/No market has no gap by construction.",
        {"what": "A plausible outcome matches no option and there is no 'Other'",
         "examples": ["Named candidates only, with a write-in possible"]},
        {"what": "The options cover every case, or include 'Other'",
         "examples": ["Bracketed ranges with an open top bracket"]},
    ),
    "title_rules_mismatch": _noul(
        "Could `title` be read as asking something different from `rules`?",
        "`title` and `rules`",
        "Traders read the title first; judge whether it would mislead them.",
        {"what": "The title is broader, narrower or differently timed than the rules",
         "examples": ["Title says 'in 2026', rules say 'by October 20'"]},
        {"what": "The title matches the rules' scope and timing"},
    ),
    # --- Scoring: an ordered rubric, not a repeat of the detections above.
    "ambiguity": Score(
        instructions={"question": "How completely do `rules` determine one outcome?",
                      "inspect": "`rules`",
                      "focus": "Judge the text as written today, not the creator's intent."},
        criteria=[
            {"what": "Airtight: every plausible outcome maps to one side"},
            {"what": "Minor gaps unlikely to decide the market"},
            {"what": "A plausible scenario is not clearly covered"},
            {"what": "Open to two readings that pick different sides"},
        ],
    ),
    # --- Classification: names the risk for the person reading the flag.
    "main_risk": Choice(
        instructions={"question": "Which flaw in `rules` is most likely to cause a dispute?",
                      "focus": "Pick the one a clarification would have to fix first."},
        criteria={
            "undefined_term": {"what": "A deciding word is undefined"},
            "subjective_judgment": {"what": "Resolution needs an opinion"},
            "no_public_evidence": {"what": "The outcome may not be observable"},
            "source": {"what": "No usable resolution source"},
            "timing": {"what": "Deadline or time zone unclear"},
            "edge_case": {"what": "A plausible scenario is uncovered"},
            "options": {"what": "The listed options miss an outcome"},
            "none": {"what": "The rules are sound"},
        },
    ),
}

def score_event(client: TypeSafeClient, e: Event) -> SystemOneResponse:
    """One Jev request per event: every question over the same state, in parallel."""
    state = {
        "title": e.title,
        "rules": e.description,
        "resolution_source": e.resolution_source,
        "end_date": e.end_date,
        "options": e.options[:MAX_OPTIONS],
    }
    return client.system_one(state, QUESTIONS, model=MODEL)
