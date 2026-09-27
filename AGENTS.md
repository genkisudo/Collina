# Repository Guidelines

## Project Structure & Module Organization

`polyflag/` contains the CLI and its pipeline: `fetch.py` retrieves Polymarket events, `score.py` asks Jev questions, `flag.py` computes deterministic dispute scores, and `report.py` displays and saves results. `__main__.py` provides the `python -m polyflag` entry point. Shared thresholds, weights, and exclusions live in `config.py`; Pydantic data models live in `models.py`. `tests/` contains pytest tests. Read `plan.md` before changing product behavior; it records the intended scope and scoring decisions. The root `score.py` only reexports `polyflag.score` for compatibility.

## Build, Test, and Development Commands

Create `.venv` with Python 3.11+ as shown in `README.md`; install `httpx`, `pydantic`, `rich`, `typesafe-sdk`, and `pytest`. There is no package build configuration in this repository.

- `.venv/bin/python -m polyflag --since 24h --threshold 0.70` scans once and prints flagged events.
- `.venv/bin/python -m polyflag --watch 300` rescans every five minutes.
- `.venv/bin/python -m pytest` runs the test suite.

The CLI needs `TYPESAFE_API_KEY` in the environment. It writes `results.json` and `seen.json` in the current working directory; avoid committing these run outputs.

## Coding Style & Naming Conventions

Follow the existing Python style: four-space indentation, snake_case modules/functions/variables, UPPER_CASE constants, and type annotations for public data and function signatures. Keep model calls in `polyflag/score.py`; downstream flagging should remain deterministic. Put tunable weights, thresholds, and filter IDs in `config.py`. No formatter or linter configuration is present, so match surrounding code.

## Testing Guidelines

Use pytest and name files `test_*.py` and cases `test_*`. Stub Jev responses when testing score composition and flag decisions, as `tests/test_flag.py` does, so routine tests do not require an API key or incur model calls. Add focused tests for changes to thresholds, confidence routing, or persistence. Run `.venv/bin/python -m pytest` before proposing a change.

## Commit & Pull Request Guidelines

No Git history is available in this directory, so no established commit message format can be inferred. Use short, imperative subjects that name the change. In pull requests, describe the behavior changed, include test results, and link a related issue when one exists. Include sample CLI output when changing reporting. Never include `TYPESAFE_API_KEY` or generated run data.

## TypeSafe Integration

Read `.agents/skills/typesafe-ai/SKILL.md` and current TypeSafe docs before changing Jev questions or SDK calls. Keep model judgments in `polyflag/score.py` and validate changes with representative events.
