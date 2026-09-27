"""Command-line entry point for fetching, scoring, and reporting events."""

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from typesafe_sdk import TypeSafeClient

from . import report
from .config import DEFAULT_THRESHOLD
from .fetch import fetch_new_events
from .flag import to_result
from .score import score_event

SEEN = Path("seen.json")

def parse_window(s: str) -> timedelta:
    """Parse a positive duration such as ``6h`` or ``3d`` for argparse."""
    match = re.fullmatch(r"([1-9][0-9]*)([hd])", s)
    if match is None:
        raise argparse.ArgumentTypeError("use a positive duration such as 6h or 3d")
    n, unit = int(match[1]), match[2]
    return {"h": timedelta(hours=n), "d": timedelta(days=n)}[unit]

def parse_threshold(s: str) -> float:
    """Accept a probability between zero and one."""
    try:
        value = float(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 1") from exc
    if not 0 <= value <= 1:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 1")
    return value

def parse_watch(s: str) -> int:
    """Accept zero to disable watch mode or a positive interval in seconds."""
    try:
        value = int(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("watch must be a nonnegative number of seconds") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("watch must be a nonnegative number of seconds")
    return value

def run_once(client: TypeSafeClient, since: datetime, threshold: float) -> None:
    """Process new events and preserve completed scores if a later call fails."""
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
    seen.update(report.scored_ids())
    events = fetch_new_events(since, seen)
    results = []
    try:
        for event in events:
            results.append(to_result(event, score_event(client, event), threshold))
    finally:
        if results:
            report.save(results)
            report.write_json(SEEN, sorted(seen | {r.event.id for r in results}))
    report.show(results, threshold)

def main() -> None:
    """Parse CLI options and run a single scan or a polling loop."""
    ap = argparse.ArgumentParser(prog="polyflag")
    ap.add_argument("--since", type=parse_window, default=timedelta(days=3),
                    help="window, e.g. 6h or 3d (default: 3d)")
    ap.add_argument("--threshold", type=parse_threshold, default=DEFAULT_THRESHOLD)
    ap.add_argument("--watch", type=parse_watch, default=0, help="rescan every N seconds")
    args = ap.parse_args()
    with TypeSafeClient() as client:
        while True:
            run_once(client, datetime.now(timezone.utc) - args.since, args.threshold)
            if not args.watch:
                break
            time.sleep(args.watch)

if __name__ == "__main__":
    main()
