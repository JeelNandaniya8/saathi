import importlib
import os
from pathlib import Path


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def execute(self, query, params=None):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("select version from schema_migrations"):
            self.rows = [{"version": version} for version in sorted(self.database.applied)]
        elif normalized.startswith("insert into schema_migrations"):
            self.database.applied.add(params[0])
        elif len(query) > 300 and "schema_migrations" not in normalized:
            self.database.migration_bodies.append(query)

    def fetchall(self):
        return list(self.rows)

    def close(self):
        return None


class FakeConnection:
    def __init__(self):
        self.applied = set()
        self.migration_bodies = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


def test_migration_runner_applies_each_file_once(monkeypatch):
    os.environ.pop("DATABASE_URL", None)
    backend = importlib.import_module("app")
    database = FakeConnection()
    monkeypatch.setattr(backend, "get_db", lambda: database)
    migration_count = len(list((Path(__file__).parents[1] / "migrations").glob("*.sql")))
    backend.run_migrations()
    assert len(database.applied) == migration_count
    first_body_count = len(database.migration_bodies)
    assert first_body_count == migration_count
    backend.run_migrations()
    assert len(database.migration_bodies) == first_body_count


def test_legacy_history_migration_is_preserving_and_idempotent():
    root = Path(__file__).parents[1]
    sql = (root / "migrations" / "002_conversations.sql").read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "previous conversation" in lowered
    assert "conversation_id is null" in lowered
    assert "delete from messages" not in lowered
    assert "on conflict" in lowered or "not exists" in lowered


def test_daily_tools_and_delivery_schema_present():
    root = Path(__file__).parents[1]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in (root / "migrations").glob("*.sql"))
    for table in ("habits", "habit_entries", "journal_entries", "trusted_contacts", "reminder_deliveries", "chat_attachments", "ai_usage_events"):
        assert f"create table if not exists {table}" in combined


def test_attachment_migration_has_private_ownership_and_cascades():
    root = Path(__file__).parents[1]
    sql = (root / "migrations" / "007_chat_attachments.sql").read_text(encoding="utf-8").lower()
    assert "user_id integer not null references users(id) on delete cascade" in sql
    assert "conversation_id integer not null references conversations(id) on delete cascade" in sql
    assert "message_id integer not null references messages(id) on delete cascade" in sql
    assert "content bytea not null" in sql


def test_ai_mode_migration_supports_safe_request_retries():
    root = Path(__file__).parents[1]
    sql = (root / "migrations" / "008_ai_study_modes.sql").read_text(encoding="utf-8").lower()
    assert "ai_mode text not null default 'normal'" in sql
    assert "client_request_id text" in sql
    assert "unique index" in sql
    assert "(user_id, conversation_id, client_request_id)" in sql
    assert "where client_request_id is not null and role = 'user'" in sql


def test_ai_usage_migration_stores_metadata_not_content():
    root = Path(__file__).parents[1]
    sql = (root / "migrations" / "009_ai_usage_events.sql").read_text(encoding="utf-8").lower()
    for column in ("ai_mode", "attachment_count", "prompt_tokens", "output_tokens", "total_tokens"):
        assert column in sql
    assert "message_content" not in sql and "file_content" not in sql


def test_message_experience_migration_is_additive_and_private():
    root = Path(__file__).parents[1]
    sql = (root / "migrations" / "010_message_experience.sql").read_text(encoding="utf-8").lower()
    assert "alter table messages" in sql
    assert "memory_labels jsonb" in sql
    assert "feedback text" in sql
    assert "drop table" not in sql and "delete from" not in sql
