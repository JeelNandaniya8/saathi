CREATE TABLE IF NOT EXISTS chat_attachments (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    mime_type TEXT NOT NULL CHECK (
        mime_type IN ('application/pdf', 'image/jpeg', 'image/png', 'image/webp')
    ),
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 8388608),
    content BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS chat_attachments_message_idx
ON chat_attachments (message_id, id);

CREATE INDEX IF NOT EXISTS chat_attachments_user_created_idx
ON chat_attachments (user_id, created_at DESC);
