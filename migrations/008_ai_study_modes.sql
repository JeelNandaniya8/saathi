ALTER TABLE messages
ADD COLUMN IF NOT EXISTS ai_mode TEXT NOT NULL DEFAULT 'normal';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS client_request_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS messages_user_request_unique_idx
ON messages (user_id, conversation_id, client_request_id)
WHERE client_request_id IS NOT NULL AND role = 'user';

CREATE INDEX IF NOT EXISTS messages_conversation_mode_idx
ON messages (conversation_id, ai_mode, id DESC);
