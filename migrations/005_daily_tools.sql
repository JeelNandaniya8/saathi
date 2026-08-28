ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'en';

CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL DEFAULT 'daily',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS habits_user_active_idx
ON habits (user_id, active, updated_at DESC);

CREATE TABLE IF NOT EXISTS habit_entries (
    id BIGSERIAL PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (habit_id, entry_date)
);
CREATE INDEX IF NOT EXISTS habit_entries_user_date_idx
ON habit_entries (user_id, entry_date DESC);

CREATE TABLE IF NOT EXISTS journal_entries (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    entry_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS journal_entries_user_date_idx
ON journal_entries (user_id, entry_date DESC, id DESC);

CREATE TABLE IF NOT EXISTS trusted_contacts (
    id BIGSERIAL PRIMARY KEY,
    owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invited_email TEXT NOT NULL,
    contact_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    allow_tasks BOOLEAN NOT NULL DEFAULT FALSE,
    allow_reminders BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (owner_user_id, invited_email)
);
CREATE INDEX IF NOT EXISTS trusted_contacts_owner_idx
ON trusted_contacts (owner_user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS trusted_contacts_invited_idx
ON trusted_contacts (invited_email, status, updated_at DESC);
