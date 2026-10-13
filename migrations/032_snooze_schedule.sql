-- A temporary snooze must not move the clock of subsequent recurring reminders.
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS snoozed_from TIMESTAMPTZ;
