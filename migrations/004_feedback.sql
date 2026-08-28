CREATE TABLE IF NOT EXISTS feedback_submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    feedback_type TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS feedback_submissions_created_idx
ON feedback_submissions (created_at DESC);
