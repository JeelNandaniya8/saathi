import importlib
import os

import pytest


@pytest.fixture(scope="module")
def client():
    os.environ.pop("DATABASE_URL", None)
    backend = importlib.import_module("app")
    backend.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    return backend.app.test_client()


@pytest.mark.parametrize("path", ["/", "/privacy", "/terms", "/limitations", "/support"])
def test_public_pages_exist(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.parametrize("path", ["/app.py", "/README.md", "/requirements.txt", "/.env", "/.git/config"])
def test_repository_files_are_not_public(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert b"Saathi backend" not in response.data
    assert b"DATABASE_URL" not in response.data


def test_health_is_honest_without_database(client):
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "configuration_required"
    assert response.get_json()["release"] == "2026-08-29-ai-study"


def test_checkout_is_disabled(client):
    response = client.get("/api/plans")
    data = response.get_json()
    assert response.status_code == 200
    assert data["checkout_enabled"] is False
    assert data["plans"]["plus"]["status"] == "coming_soon"
    assert data["plans"]["family"]["status"] == "coming_soon"
    assert data["attachment_entitlements"]["free"]["attachments_enabled"] is True


def test_csrf_required_for_authenticated_mutations(client):
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["csrf_token"] = "known-token"
    blocked = client.post("/api/upgrade", json={"plan": "plus"})
    assert blocked.status_code == 403
    allowed = client.post(
        "/api/upgrade",
        json={"plan": "plus"},
        headers={"X-CSRF-Token": "known-token"},
    )
    assert allowed.status_code == 503
    assert allowed.get_json()["checkout_enabled"] is False


def test_cross_origin_mutation_is_blocked(client):
    response = client.post(
        "/api/support",
        json={"type": "general", "message": "hello"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403


def test_reminder_scheduler_requires_a_secret(client):
    response = client.post("/api/cron/reminders")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Not authorised."


def test_daily_tool_and_preferences_routes_are_registered(client):
    routes = {rule.rule for rule in client.application.url_map.iter_rules()}
    assert {
        "/api/habits",
        "/api/habits/<int:habit_id>",
        "/api/journal",
        "/api/journal/<int:entry_id>",
        "/api/trusted-contacts",
        "/api/preferences",
        "/api/attachments/<int:attachment_id>",
    } <= routes


def test_attachment_download_requires_login(client):
    with client.session_transaction() as session:
        session.clear()
    response = client.get("/api/attachments/99")
    assert response.status_code == 401
    assert response.get_json()["login_required"] is True
    assert response.headers["Cache-Control"] == "no-store"
