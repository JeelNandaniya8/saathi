ALTER TABLE messages ADD COLUMN IF NOT EXISTS request_fingerprint TEXT;

CREATE TABLE IF NOT EXISTS chat_request_cancellations (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    request_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id,conversation_id,request_id)
);

ALTER TABLE messages ADD COLUMN IF NOT EXISTS regeneration_request_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS messages_regeneration_request ON messages(user_id,regeneration_request_id) WHERE regeneration_request_id IS NOT NULL;
