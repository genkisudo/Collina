"""Render flagged results and persist every scored event as JSON."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from rich.console import Console
from rich.table import Table
from .config import LOW_CONFIDENCE
from .models import Result

def show(results: list[Result], threshold: float) -> None:
    """Print flagged events in descending score order and a scan summary."""

    flagged = sorted((r for r in results if r.flagged), key=lambda r: -r.p)
    table = Table(title=f"Events at p >= {threshold:.2f}")
    for col in ["p", "Event", "Top reasons", "Main risk", "Created (UTC)", "Link"]:
        table.add_column(col)
    for r in flagged:
        note = " (low confidence)" if r.ambiguity_confidence < LOW_CONFIDENCE else ""
        table.add_row(f"{r.p:.2f}", r.event.title[:60],
                      ", ".join(f"{k} {v:.2f}" for k, v in list(r.reasons.items())[:3]) + note,
                      r.main_risk, r.event.created_at.strftime("%Y-%m-%d %H:%M"),
                      f"https://polymarket.com/event/{r.event.slug}")
    console = Console()
    if flagged:
        console.print(table)
    console.print(f"Scanned {len(results)} new events, {len(flagged)} flagged at p >= {threshold:.2f}")

def save(results: list[Result], path: str = "results.json") -> None:
    """Append scored events to a JSON file for later review and reweighting."""

    old = json.loads(Path(path).read_text()) if Path(path).exists() else []
    old += [r.model_dump(mode="json") for r in results]
    write_json(path, old)

def write_json(path: str | Path, value: object) -> None:
    """Replace a JSON file atomically so interrupted writes keep the old data."""

    destination = Path(path)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                            prefix=f".{destination.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

def scored_ids(path: str = "results.json") -> set[str]:
    """Recover scored IDs when results were saved before seen.json was updated."""

    if not Path(path).exists():
        return set()
    return {str(record["event"]["id"]) for record in json.loads(Path(path).read_text())}
