CREATE TABLE IF NOT EXISTS focus_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    client_id UUID NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK(duration_seconds IN (1500,3000)),
    elapsed_seconds INTEGER NOT NULL DEFAULT 0 CHECK(elapsed_seconds>=0),
    status TEXT NOT NULL CHECK(status IN ('running','paused','completed','cancelled')),
    last_started_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id,client_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS focus_one_active ON focus_sessions(user_id) WHERE status IN ('running','paused');
CREATE INDEX IF NOT EXISTS focus_owner_recent ON focus_sessions(user_id,id DESC);
