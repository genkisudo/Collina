"""Fetch newly created, eligible events from Polymarket's Gamma API."""

from datetime import datetime
import re
import httpx
from .config import EXCLUDE_TAG_IDS, PRICE_TITLE
from .models import Event

GAMMA = "https://gamma-api.polymarket.com/events"
PRICE_RE = re.compile(PRICE_TITLE, re.IGNORECASE)

def _parse_time(s: str) -> datetime:
    """Parse an ISO 8601 timestamp, including Gamma's UTC suffix."""

    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def _to_event(r: dict) -> Event:
    """Map one Gamma event to the fields used by the scoring pipeline."""

    markets = [m for m in r.get("markets") or [] if m.get("active") and not m.get("closed")]
    return Event(
        id=str(r["id"]), slug=r["slug"], title=r["title"],
        description=r.get("description") or "",
        resolution_source=r.get("resolutionSource") or "",
        end_date=r.get("endDate"),
        created_at=_parse_time(r["createdAt"]),
        options=[m.get("groupItemTitle") or m.get("question") or "" for m in markets],
    )

def fetch_new_events(since: datetime, seen: set[str], page: int = 100,
                     max_pages: int = 10,
                     transport: httpx.BaseTransport | None = None) -> list[Event]:
    """Newest-first events created after `since`, minus seen ids and price titles."""
    out: list[Event] = []
    with httpx.Client(timeout=30, transport=transport) as http:
        for i in range(max_pages):
            params = [("active", "true"), ("closed", "false"),
                      ("order", "createdAt"), ("ascending", "false"),
                      ("limit", page), ("offset", i * page)]
            params += [("exclude_tag_id", t) for t in EXCLUDE_TAG_IDS]
            resp = http.get(GAMMA, params=params)
            resp.raise_for_status()
            rows = resp.json()
            for r in rows:
                if not r.get("createdAt"):
                    continue
                if _parse_time(r["createdAt"]) < since:
                    return out
                if str(r["id"]) not in seen and not PRICE_RE.search(r["title"]):
                    event = _to_event(r)
                    if event.options:
                        out.append(event)
            if len(rows) < page:
                break
    return out
