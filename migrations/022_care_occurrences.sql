ALTER TABLE reminders ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'general';
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS care_schedule JSONB;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS current_scheduled_for TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS care_occurrences (
    id BIGSERIAL PRIMARY KEY,
    reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scheduled_for TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','taken','skipped','not_confirmed')),
    reported_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(reminder_id,scheduled_for)
);
CREATE INDEX IF NOT EXISTS care_occurrences_owner_idx ON care_occurrences(user_id,scheduled_for DESC);
ALTER TABLE push_deliveries ADD COLUMN IF NOT EXISTS care_occurrence_id BIGINT REFERENCES care_occurrences(id) ON DELETE CASCADE;
