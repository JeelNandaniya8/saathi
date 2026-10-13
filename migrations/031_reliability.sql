CREATE TABLE IF NOT EXISTS chat_action_previews (
  message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  draft JSONB NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '15 minutes'
);
CREATE TABLE IF NOT EXISTS study_jobs (
  id UUID PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK(kind IN ('mock','map')),
  request JSONB NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('creating','ready','failed')),
  result_id INTEGER,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS study_jobs_owner ON study_jobs(user_id,created_at DESC);
ALTER TABLE workspace_preferences ALTER COLUMN timezone SET DEFAULT 'Asia/Kolkata';
