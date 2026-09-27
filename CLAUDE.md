# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**polyflag**: a Python CLI that pulls newly created Polymarket events from the public Gamma API and asks TypeSafe's Jev model one batch of typed questions per event about its rules. It prints only the events whose dispute probability `p` is at or above a threshold. `plan.md` is the full spec and the source of truth for design decisions, including the reasoning behind the tag exclusions, the weights and the confidence routing. Read it before changing behavior.

The core principle: **Jev detects the ingredients of contention, and ordinary Python decides whether a market is flagged.** Only `score.py` calls a model. Everything after it is deterministic code.

When working on the Jev questions or the SDK calls, read `.agents/skills/typesafe-ai/SKILL.md` and check the live docs at https://docs.typesafe.ai/llms.txt. Do not guess SDK signatures.

## Current state of the repo

The package is built and matches the target layout below. `fetch.py` is live-verified against the Gamma API (23 events on 2026-09-27, matching `plan.md`'s reported count, no sports/crypto/price markets). `flag.py` is covered by `tests/test_flag.py` with stubbed Jev answers. Every module imports cleanly against the installed `typesafe-sdk` (0.7.2).

Not yet verified: the live `score_event` Jev call, since no `TYPESAFE_API_KEY` was available in the building session. Run `python -m polyflag` with a real key to confirm the `QUESTIONS` shape and `SystemOneResponse` field access (`r.nouls[k].noul`, `r.scores["ambiguity"]`, `r.choices["main_risk"]`) end-to-end.

`Result.model` (the versioned model id that answered, e.g. `jev-1.13.0`) was added beyond `plan.md`'s draft so results.json records exactly which model produced each score, per the Models page's guidance on pinned vs. aliased versions.

Layout:

```
polyflag/  __init__.py  __main__.py  config.py  models.py  fetch.py  score.py  flag.py  report.py
tests/     __init__.py  test_flag.py
```

## Commands

Requires Python 3.11+ with `httpx`, `pydantic`, `rich` and `typesafe-sdk`. `TYPESAFE_API_KEY` must be set in the environment.

```bash
python -m polyflag --since 24h --threshold 0.70   # one shot (defaults: --since 3d, --threshold 0.60)
python -m polyflag --watch 300 --threshold 0.70   # rescan every 5 min, new events only
pytest tests/test_flag.py                          # once tests exist; flag.py is testable with stubbed Jev answers
```

Runtime files are written to the working directory. `results.json` gets every scored event appended, flagged or not. `seen.json` holds the ids of events that were already scored, so they are never rescored.

## Pipeline

`fetch → score → flag → report`, run by `__main__.run_once`:

1. **fetch.py**: pages `GET /events` sorted by `createdAt` descending and stops at the first event older than `--since`. It excludes sports, crypto and price markets with `EXCLUDE_TAG_IDS` and a `PRICE_TITLE` regex on the title, since tags miss some price markets. It also skips ids in `seen.json`. Only open markets are kept, and their `groupItemTitle` values become the event's `options`.
2. **score.py**: exactly **one** `client.system_one(...)` call per event, with model `jev-1.13.0` pinned. The state is `title`, `rules` (the event description), `resolution_source`, `end_date` and `options[:30]`. `QUESTIONS` holds 8 detection Nouls, one `ambiguity` Score with 4 levels (0–3) and one `main_risk` Choice. All of them run in parallel over the same state. The questions refer to the state by backticked path, for example `` `rules` ``.
3. **flag.py**: `p = Σ WEIGHTS[k] · s_k`, where each `s_k` is a Noul probability, or `ambiguity / 3` for the Score. The weights sum to 1. Nouls at or above `REASON_MIN` (0.50) become the displayed reasons. Confidence is routed separately from `p`: `main_risk` shows as `"unclear"` when its confidence is below `HIGH_CONFIDENCE` (0.70).
4. **report.py**: a rich table of flagged events only, highest `p` first. A `(low confidence)` note is added when the ambiguity confidence is below `LOW_CONFIDENCE`. It also appends to `results.json`.

## Design rules to preserve

- To change what gets flagged, tune `WEIGHTS` and the thresholds in `config.py`, not the questions. The raw `nouls` are saved so results can be re-weighted without rescoring.
- Keep one narrow judgment per question. Don't collapse them into a single "is this contentious?" question.
- A key in `WEIGHTS` must match a Noul id in `QUESTIONS`, or be `ambiguity`. `dispute_risk` indexes every weight key.
- Tag ids and the price regex are in `config.py` because Polymarket can change them.
- Out of scope for v1: trading, a web UI, rule rewrites, UMA outcome prediction and backtesting.
