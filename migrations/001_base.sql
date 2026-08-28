CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    plan_status TEXT NOT NULL DEFAULT 'active',
    session_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS pending_verifications (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    otp_code TEXT NOT NULL DEFAULT 'hashed',
    otp_hash TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_sent_at TIMESTAMPTZ
);
ALTER TABLE pending_verifications ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE pending_verifications ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ;
ALTER TABLE pending_verifications ADD COLUMN IF NOT EXISTS otp_hash TEXT;

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS password_resets (
    email TEXT PRIMARY KEY,
    otp_code TEXT NOT NULL DEFAULT 'hashed',
    otp_hash TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_sent_at TIMESTAMPTZ
);
ALTER TABLE password_resets ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE password_resets ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ;
ALTER TABLE password_resets ADD COLUMN IF NOT EXISTS otp_hash TEXT;

CREATE TABLE IF NOT EXISTS request_attempts (
    id BIGSERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    identifier_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS request_attempts_lookup_idx
ON request_attempts (action, identifier_hash, created_at DESC);

DELETE FROM pending_verifications WHERE otp_hash IS NULL;
DELETE FROM password_resets WHERE otp_hash IS NULL;
