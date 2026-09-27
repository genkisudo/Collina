"""Regression tests for fetching, CLI validation, and interrupted scans."""

import argparse
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from polyflag import __main__ as cli
from polyflag.fetch import fetch_new_events
from polyflag.models import Event, Result
from polyflag.score import QUESTIONS, score_event


def test_fetch_skips_events_without_open_markets():
    rows = [
        {"id": "closed", "slug": "closed", "title": "Closed options",
         "createdAt": "2026-09-27T12:00:00Z",
         "markets": [{"active": False, "closed": True, "question": "Closed"}]},
        {"id": "open", "slug": "open", "title": "Open options",
         "createdAt": "2026-09-27T11:00:00Z",
         "markets": [{"active": True, "closed": False, "question": "Open"}]},
    ]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=rows))

    events = fetch_new_events(datetime(2026, 9, 27, tzinfo=timezone.utc), set(),
                              transport=transport)

    assert [event.id for event in events] == ["open"]
    assert events[0].options == ["Open"]


@pytest.mark.parametrize("value", ["", "0h", "-1d", "1m", "3dextra"])
def test_parse_window_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.parse_window(value)


@pytest.mark.parametrize("value", ["-0.1", "1.1", "nan", "text"])
def test_parse_threshold_rejects_out_of_range_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.parse_threshold(value)


def test_score_event_sends_all_context_in_one_request():
    event = Event(id="1", slug="one", title="Will it happen?", description="Rules",
                  resolution_source="Official report", end_date="2026-10-01T00:00:00Z",
                  created_at=datetime(2026, 9, 27, tzinfo=timezone.utc), options=["Yes", "No"])

    class Client:
        def system_one(self, state, questions, *, model):
            assert state == {
                "title": event.title, "rules": event.description,
                "resolution_source": event.resolution_source,
                "end_date": event.end_date, "options": event.options,
            }
            assert questions is QUESTIONS
            assert model == "jev-1.13.0"
            return "response"

    assert score_event(Client(), event) == "response"


def test_completed_scores_survive_later_model_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SEEN", tmp_path / "seen.json")
    events = [
        Event(id=id_, slug=id_, title=id_, description="Rules", resolution_source="",
              end_date=None, created_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
              options=["Yes", "No"])
        for id_ in ("first", "second")
    ]
    monkeypatch.setattr(cli, "fetch_new_events", lambda since, seen: events)

    def score(client, event):
        if event.id == "second":
            raise RuntimeError("model unavailable")
        return SimpleNamespace()

    def result(event, response, threshold):
        return Result(event=event, p=0.8, flagged=True, ambiguity_score=2,
                      ambiguity_confidence=0.9, main_risk="undefined_term",
                      main_risk_confidence=0.9, reasons={"undefined_term": 0.8},
                      nouls={"undefined_term": 0.8}, model="jev-1.13.0")

    monkeypatch.setattr(cli, "score_event", score)
    monkeypatch.setattr(cli, "to_result", result)

    with pytest.raises(RuntimeError, match="model unavailable"):
        cli.run_once(object(), datetime(2026, 9, 27, tzinfo=timezone.utc), 0.6)

    assert json.loads((tmp_path / "seen.json").read_text()) == ["first"]
    assert [row["event"]["id"] for row in json.loads((tmp_path / "results.json").read_text())] == ["first"]
