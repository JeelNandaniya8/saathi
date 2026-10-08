CREATE TABLE IF NOT EXISTS classroom_oauth_requests (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 state_hash TEXT NOT NULL UNIQUE, verifier_cipher TEXT NOT NULL,
 session_version INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS classroom_connections (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 refresh_cipher TEXT NOT NULL, selected_courses JSONB NOT NULL DEFAULT '[]',
 course_catalog JSONB NOT NULL DEFAULT '[]', last_sync TIMESTAMPTZ,
 last_error TEXT, version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS classroom_assignments (
 id BIGSERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 course_id TEXT NOT NULL, external_id TEXT NOT NULL, title TEXT NOT NULL,
 instructions TEXT NOT NULL DEFAULT '', original_url TEXT NOT NULL DEFAULT '',
 due_at TIMESTAMPTZ, deadline_uncertain BOOLEAN NOT NULL DEFAULT FALSE,
 available BOOLEAN NOT NULL DEFAULT TRUE, synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
 UNIQUE(user_id,course_id,external_id)
);
CREATE INDEX IF NOT EXISTS classroom_assignments_owner ON classroom_assignments(user_id,due_at);
