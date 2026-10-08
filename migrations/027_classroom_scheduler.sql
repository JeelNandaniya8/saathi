ALTER TABLE classroom_connections ADD COLUMN IF NOT EXISTS auto_sync_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE classroom_connections ADD COLUMN IF NOT EXISTS next_sync_at TIMESTAMPTZ;
ALTER TABLE classroom_connections ADD COLUMN IF NOT EXISTS last_attempt TIMESTAMPTZ;
ALTER TABLE classroom_connections ADD COLUMN IF NOT EXISTS sync_failures INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS classroom_sync_due ON classroom_connections(next_sync_at,user_id) WHERE auto_sync_enabled=TRUE;
