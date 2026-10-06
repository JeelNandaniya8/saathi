CREATE TABLE IF NOT EXISTS plan_waitlist (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL,
    plan TEXT NOT NULL CHECK (plan IN ('plus', 'family')),
    language TEXT NOT NULL DEFAULT 'en' CHECK (language IN ('en', 'gu', 'hi')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, plan)
);
