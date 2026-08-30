import importlib
import os
import base64
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace

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


def test_otp_expiry_rejects_the_exact_ten_minute_boundary(backend):
    expires_at = datetime(2026, 8, 29, 4, 15, tzinfo=timezone.utc)
    assert backend.otp_is_expired(expires_at, expires_at - timedelta(microseconds=1)) is False
    assert backend.otp_is_expired(expires_at, expires_at) is True
    assert backend.otp_is_expired(expires_at, expires_at + timedelta(seconds=1)) is True
    assert backend.otp_is_expired(None, expires_at) is True


@pytest.mark.parametrize("remember", [False, True])
def test_session_duration_is_an_explicit_user_choice(backend, remember):
    user = {"id": 7, "session_version": 3}
    with backend.app.test_request_context():
        backend.start_user_session(user, remember)
        assert backend.session["user_id"] == 7
        assert backend.session["session_version"] == 3
        assert backend.session["csrf_token"]
        assert backend.session.permanent is remember


@pytest.mark.parametrize(("remember", "has_expiry"), [(False, False), (True, True)])
def test_login_cookie_expiry_matches_remember_choice(backend, monkeypatch, remember, has_expiry):
    user = {
        "id": 7,
        "name": "Test Student",
        "username": "test_student",
        "email": "student@example.com",
        "password_hash": "stored-hash",
        "plan": "free",
        "plan_status": "active",
        "language": "en",
        "session_version": 3,
        "created_at": datetime(2026, 8, 29, tzinfo=timezone.utc),
    }

    class Cursor:
        def execute(self, query, params=None):
            assert "SELECT * FROM users WHERE email" in query

        def fetchone(self):
            return user

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(backend, "limited", lambda *_args: None)
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    monkeypatch.setattr(backend, "check_password_hash", lambda *_args: True)
    response = backend.app.test_client().post(
        "/api/login",
        json={"email": user["email"], "password": "Saathi123", "remember": remember},
    )
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert ("Expires=" in cookie) is has_expiry
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_login_rejects_non_boolean_remember_preference(backend):
    response = backend.app.test_client().post(
        "/api/login",
        json={"email": "student@example.com", "password": "Saathi123", "remember": "yes"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Choose a valid sign-in preference."


def test_expired_correct_password_reset_code_cannot_change_password(backend, monkeypatch):
    executed = []
    pending = {
        "email": "student@example.com",
        "otp_hash": backend.generate_password_hash("123456"),
        "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
        "attempt_count": 0,
    }

    class Cursor:
        def execute(self, query, params=None):
            executed.append(query)
            assert "SELECT * FROM password_resets" in query

        def fetchone(self):
            return pending

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(backend, "limited", lambda *_args: None)
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    response = backend.app.test_client().post(
        "/api/reset-password",
        json={"email": "student@example.com", "otp": "123456", "password": "NewSaathi123"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "This code has expired. Please request a new one."
    assert not any("UPDATE users" in query for query in executed)


def test_expired_signup_code_cannot_create_account(backend, monkeypatch):
    executed = []
    pending = {
        "otp_hash": backend.generate_password_hash("654321"),
        "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
        "attempt_count": 0,
    }

    class Cursor:
        def execute(self, query, params=None):
            executed.append(query)
            assert "SELECT * FROM pending_verifications" in query

        def fetchone(self):
            return pending

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(backend, "limited", lambda *_args: None)
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    response = backend.app.test_client().post(
        "/api/verify-otp",
        json={"email": "student@example.com", "otp": "654321", "remember": False},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "This code has expired. Please request a new one."
    assert not any("INSERT INTO users" in query for query in executed)


def test_logout_all_devices_invalidates_sessions_and_clears_current_cookie(backend, monkeypatch):
    class Cursor:
        def execute(self, query, params=None):
            assert "session_version = session_version + 1" in query
            assert params == (7,)

        def fetchone(self):
            return {"id": 7}

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(backend, "require_user_id", lambda: 7)
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    client = backend.app.test_client()
    with client.session_transaction() as current:
        current["user_id"] = 7
        current["csrf_token"] = "known-token"
    response = client.post(
        "/api/logout-all", json={}, headers={"X-CSRF-Token": "known-token"}
    )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    with client.session_transaction() as current:
        assert "user_id" not in current
        assert "csrf_token" not in current


def test_health_reports_release_without_exposing_configuration(backend, monkeypatch):
    class Cursor:
        def execute(self, query):
            assert query == "SELECT 1"

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(backend, "DATABASE_URL", "configured")
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    response = backend.app.test_client().get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "release": "2026-08-30-ai-experience",
    }


@pytest.mark.parametrize(
    ("path", "destination"),
    (("/chat", "/account?next=/chat"), ("/dashboard", "/account?next=/dashboard")),
)
def test_private_pages_redirect_before_rendering_when_logged_out(backend, path, destination):
    response = backend.app.test_client().get(path)
    assert response.status_code == 302
    assert response.headers["Location"].endswith(destination)


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
    assert backend.generate_gemini_reply(messages, "- Goal: exam", "gu", "deep_study") == "Ready."
    assert len(captured["payload"]["contents"]) <= 30
    assert sum(len(item["parts"][0]["text"]) for item in captured["payload"]["contents"]) <= 40000
    system = captured["payload"]["systemInstruction"]["parts"][0]["text"]
    assert "USER-CONTROLLED MEMORY" in system
    assert "Gujarati" in system
    assert "ACTIVE RESPONSE MODE" in system
    assert "Deep study" in system
    assert captured["payload"]["generationConfig"]["temperature"] == 0.45
    assert captured["payload"]["generationConfig"]["maxOutputTokens"] == 1500
    assert "generativelanguage.googleapis.com" in captured["url"]


def test_chat_modes_are_server_validated(backend):
    assert backend.normalise_chat_mode("quiz") == "quiz"
    assert backend.normalise_chat_mode("DEEP_STUDY") == "deep_study"
    assert backend.normalise_chat_mode("invented-unrestricted-mode") == "normal"
    assert {"normal", "explain", "deep_study", "summarise", "quiz", "flashcards", "study_plan"}.issubset(backend.CHAT_MODES)
    assert "Summarise" in backend.default_attachment_prompt("summarise", 1)
    assert "one question at a time" in backend.default_attachment_prompt("quiz", 2)
    assert backend.default_attachment_prompt("unknown", 1) == "Please explain the attached file."
    assert backend.make_attachment_conversation_title(
        "summarise", [{"name": "Physics_notes.pdf"}]
    ) == "Summary · Physics_notes.pdf"
    assert backend.make_attachment_conversation_title(
        "normal", [{"name": "diagram.png"}, {"name": "chapter.pdf"}]
    ) == "diagram.png +1"


def test_attachment_magic_validation_and_limits(backend):
    entitlement = backend.PLAN_ENTITLEMENTS["free"]
    pdf = SimpleNamespace(filename="My lesson.PDF", stream=BytesIO(b"%PDF-1.7\ncontent"))
    prepared = backend.prepare_chat_attachments([pdf], entitlement)
    assert prepared[0]["name"] == "My_lesson.pdf"
    assert prepared[0]["mime_type"] == "application/pdf"
    assert prepared[0]["size_bytes"] == len(b"%PDF-1.7\ncontent")

    disguised = SimpleNamespace(filename="notes.pdf", stream=BytesIO(b"not really a pdf"))
    with pytest.raises(ValueError, match="PDF, JPG, PNG or WebP"):
        backend.prepare_chat_attachments([disguised], entitlement)

    second = SimpleNamespace(filename="second.pdf", stream=BytesIO(b"%PDF-1.7\nsecond"))
    with pytest.raises(ValueError, match="up to 1"):
        backend.prepare_chat_attachments([pdf, second], entitlement)

    empty = SimpleNamespace(filename="empty.png", stream=BytesIO(b""))
    with pytest.raises(ValueError, match="Empty files"):
        backend.prepare_chat_attachments([empty], entitlement)

    first_content = b"%PDF-1.7\nfirst"
    second_content = b"%PDF-1.7\nsecond"
    total_limited = {
        **backend.PLAN_ENTITLEMENTS["plus"],
        "attachment_total_bytes": len(first_content) + len(second_content) - 1,
    }
    first = SimpleNamespace(filename="first.pdf", stream=BytesIO(first_content))
    second = SimpleNamespace(filename="second.pdf", stream=BytesIO(second_content))
    with pytest.raises(ValueError, match="can total up to"):
        backend.prepare_chat_attachments([first, second], total_limited)


def test_gemini_multimodal_payload_contains_inline_file(backend, monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": "It is a chart."}]}}],
                "usageMetadata": {
                    "promptTokenCount": 42,
                    "candidatesTokenCount": 7,
                    "totalTokenCount": 49,
                },
            }

    def fake_post(url, json, timeout):
        captured.update(payload=json)
        return Response()

    monkeypatch.setattr(backend, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(backend.requests, "post", fake_post)
    content = b"\x89PNG\r\n\x1a\nexample"
    reply, usage = backend.generate_gemini_reply([{
        "role": "user",
        "content": "Explain this image.",
        "attachments": [{"mime_type": "image/png", "content": content}],
    }], include_usage=True)
    assert reply == "It is a chart."
    assert usage == {"prompt_tokens": 42, "output_tokens": 7, "total_tokens": 49}
    parts = captured["payload"]["contents"][0]["parts"]
    assert parts[0]["text"] == "Explain this image."
    assert parts[1]["inlineData"]["mimeType"] == "image/png"
    assert parts[1]["inlineData"]["data"] == base64.b64encode(content).decode("ascii")


def test_completed_chat_request_replays_without_duplicate(backend):
    now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)

    class Cursor:
        def __init__(self):
            self.rows = []

        def execute(self, query, params=None):
            if "FROM messages" in query:
                self.rows = [
                    {"id": 10, "role": "user", "content": "Explain this", "created_at": now, "ai_mode": "explain"},
                    {"id": 11, "role": "assistant", "content": "Ready", "created_at": now, "ai_mode": "explain"},
                ]
            elif "FROM chat_attachments" in query:
                self.rows = []

        def fetchall(self):
            return list(self.rows)

    conversation = {"id": 3, "title": "Lesson", "created_at": now, "updated_at": now}
    replay = backend.completed_chat_request(Cursor(), conversation, 7, "request_123456789")
    assert replay["replayed"] is True
    assert replay["user_message"]["ai_mode"] == "explain"
    assert replay["assistant_message"]["content"] == "Ready"


def test_ai_usage_records_counts_without_content(backend):
    captured = {}

    class Cursor:
        def execute(self, query, params=None):
            captured["query"] = query
            captured["params"] = params

    now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
    backend.record_ai_usage(
        Cursor(), 7, 3, "quiz", 1,
        {"prompt_tokens": 20, "output_tokens": 5, "total_tokens": 25}, now,
    )
    assert "INSERT INTO ai_usage_events" in captured["query"]
    assert captured["params"][0:7] == (7, 3, "quiz", 1, 20, 5, 25)
    assert "message" not in captured["query"].lower()


def test_attachment_usage_payload_keeps_retry_allowance_current(backend):
    class Cursor:
        def execute(self, query, params=None):
            assert "FROM chat_attachments" in query
            assert params[0] == 7

        def fetchone(self):
            return {"count": 3}

    payload = backend.attachment_usage_payload(
        Cursor(), 7, backend.PLAN_ENTITLEMENTS["free"]
    )
    assert payload == {"used_today": 3, "remaining_today": 2, "per_day": 5}


def test_message_payload_exposes_only_saved_memory_labels_and_feedback(backend):
    now = datetime(2026, 8, 30, 8, tzinfo=timezone.utc)
    payload = backend.message_to_dict({
        "id": 42,
        "role": "assistant",
        "content": "A clear answer",
        "created_at": now,
        "ai_mode": "explain",
        "memory_labels": ["Study goal", "Preferred language"],
        "feedback": "helpful",
    })
    assert payload["memory_labels"] == ["Study goal", "Preferred language"]
    assert payload["feedback"] == "helpful"
    assert "memory_content" not in payload


def test_message_feedback_is_limited_to_owned_assistant_message(backend, monkeypatch):
    executed = {}

    class Cursor:
        def execute(self, query, params=None):
            executed["query"] = query
            executed["params"] = params

        def fetchone(self):
            return {"id": 42, "feedback": "helpful"}

        def close(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(backend, "require_user_id", lambda: 7)
    monkeypatch.setattr(backend, "limited", lambda *_args: None)
    monkeypatch.setattr(backend, "get_db", lambda: Connection())
    client = backend.app.test_client()
    with client.session_transaction() as current:
        current["user_id"] = 7
        current["csrf_token"] = "known-token"
    response = client.patch(
        "/api/messages/42/feedback",
        json={"rating": "helpful"},
        headers={"X-CSRF-Token": "known-token"},
    )
    assert response.status_code == 200
    assert response.get_json() == {"message_id": 42, "feedback": "helpful"}
    assert "role = 'assistant'" in executed["query"]
    assert executed["params"] == ("helpful", 42, 7)
