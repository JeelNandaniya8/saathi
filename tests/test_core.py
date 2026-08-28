import importlib
import os
from datetime import date, datetime, timedelta, timezone

import pytest


@pytest.fixture(scope="module")
def backend():
    os.environ.pop("DATABASE_URL", None)
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    return module


def test_validation_rules(backend):
    assert backend.validate_name("Jeel Nandaniya") is None
    assert backend.validate_name("J1")
    assert backend.validate_username("jeel_8") is None
    assert backend.validate_username("no spaces")
    assert backend.validate_password("Saathi123") is None
    assert backend.validate_password("onlyletters")


def test_recurring_reminder_calculation(backend):
    now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
    due = now - timedelta(days=15)
    daily, active = backend.next_reminder_occurrence(due, "daily", now)
    assert active is True and daily > now
    assert daily - now <= timedelta(days=1)
    weekly, active = backend.next_reminder_occurrence(due, "weekly", now)
    assert active is True and weekly > now
    assert weekly - now <= timedelta(days=7)
    once, active = backend.next_reminder_occurrence(due, "once", now)
    assert once == due and active is False


def test_habit_streaks(backend):
    today = date(2026, 8, 28)
    assert backend.habit_streak([today, today - timedelta(days=1)], "daily", today) == 2
    monday = date(2026, 8, 31)
    friday = monday - timedelta(days=3)
    thursday = monday - timedelta(days=4)
    assert backend.habit_streak([friday, thursday], "weekdays", monday) == 2
    assert backend.habit_streak([today, today - timedelta(days=7)], "weekly", today) == 2


def test_gemini_context_limits_and_language(backend, monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "Ready."}]}}]}

    def fake_post(url, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(backend, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(backend.requests, "post", fake_post)
    messages = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"message {index}"}
        for index in range(60)
    ]
    assert backend.generate_gemini_reply(messages, "- Goal: exam", "gu") == "Ready."
    assert len(captured["payload"]["contents"]) <= 30
    assert sum(len(item["parts"][0]["text"]) for item in captured["payload"]["contents"]) <= 40000
    system = captured["payload"]["systemInstruction"]["parts"][0]["text"]
    assert "USER-CONTROLLED MEMORY" in system
    assert "Gujarati" in system
    assert "generativelanguage.googleapis.com" in captured["url"]
