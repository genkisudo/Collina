# Polyflag

Polyflag is a Python CLI that reviews newly listed Polymarket events for resolution rules that may cause confusion or disputes. It fetches eligible events from the public Gamma API, asks TypeSafe Jev a batch of focused questions about each event, then combines the answers with fixed weights in Python. The terminal shows events at or above your dispute threshold; every scored event is saved for later review.

## Requirements and setup

Use Python 3.11 or newer and a TypeSafe API key. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install httpx pydantic rich typesafe-sdk pytest
export TYPESAFE_API_KEY="your-key"
```

The repository currently uses `venv` and `pip`; it has no `uv.lock` or package build configuration.

The Gamma API needs no credential. Keep `TYPESAFE_API_KEY` out of source files and commits.

## Run

```sh
.venv/bin/python -m polyflag
.venv/bin/python -m polyflag --since 24h --threshold 0.70
.venv/bin/python -m polyflag --watch 300
```

`--since` accepts a positive number of hours (`6h`) or days (`3d`); the default is `3d`. `--threshold` accepts a value from `0` to `1` and defaults to `0.60`. `--watch` rescans every N seconds; omit it for one scan. Watch mode moves the time window forward on each scan.

The CLI writes `results.json` with every scored event and its raw signals, even when the event is not flagged. `seen.json` records scored event IDs so later scans do not repeat model calls. Both files are created in the directory from which you run the command and are ignored by Git. Clear both files only when you intentionally want to rescore events.

## How it works

`polyflag/fetch.py` pages new open Gamma events and excludes tagged sports, crypto, stock, commodity, recurring, and hidden events, plus titles that match the price filter. `polyflag/score.py` sends one Jev request per event with eight yes/no checks, an ambiguity score, and a main-risk choice. `polyflag/flag.py` combines the probabilities using weights in `polyflag/config.py`; `polyflag/report.py` prints flagged events and saves all results. Only `score.py` calls the model. See `plan.md` for the design rationale.

## Tests and limitations

Run `.venv/bin/python -m pytest`. The tests use stubbed model answers and HTTP responses, so they need no API key. A live Jev call still requires a valid key and network access; the local tests do not establish how well the model identifies contentious real-world rules. Thresholds and weights are starting values rather than measured accuracy guarantees.

For SDK details, see the [TypeSafe Python documentation](https://docs.typesafe.ai/sdk/python) and the installed skill at `.agents/skills/typesafe-ai/SKILL.md`.
