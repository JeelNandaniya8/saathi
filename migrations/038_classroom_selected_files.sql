-- Metadata remains NULL for old imports until the next ordinary selected-course sync.
ALTER TABLE classroom_assignments ADD COLUMN IF NOT EXISTS file_materials JSONB;
CREATE TABLE IF NOT EXISTS classroom_file_grants (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES classroom_connections(user_id) ON DELETE CASCADE,
    assignment_id BIGINT NOT NULL REFERENCES classroom_assignments(id) ON DELETE CASCADE,
    drive_id TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    connection_version INTEGER NOT NULL,
    session_version INTEGER NOT NULL,
    access_cipher TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    download_hash TEXT
);
CREATE INDEX IF NOT EXISTS classroom_file_grants_owner_expiry ON classroom_file_grants(user_id,expires_at);
