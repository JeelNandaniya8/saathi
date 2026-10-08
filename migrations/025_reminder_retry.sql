ALTER TABLE reminders ADD COLUMN IF NOT EXISTS client_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS reminders_owner_client_idx ON reminders(user_id,client_id) WHERE client_id IS NOT NULL;
