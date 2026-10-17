-- Older imports have no verified submission state; never assume they are pending.
ALTER TABLE classroom_assignments ADD COLUMN IF NOT EXISTS submission_state TEXT NOT NULL DEFAULT 'UNKNOWN'
    CHECK (submission_state IN ('UNKNOWN','NEW','CREATED','TURNED_IN','RETURNED','RECLAIMED_BY_STUDENT'));
ALTER TABLE classroom_connections ADD COLUMN IF NOT EXISTS submission_sync_at TIMESTAMPTZ;
