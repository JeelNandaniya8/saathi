CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New conversation',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE;

WITH legacy_users AS (
    SELECT user_id, MIN(created_at) AS created_at, MAX(created_at) AS updated_at
    FROM messages
    WHERE conversation_id IS NULL
    GROUP BY user_id
), created AS (
    INSERT INTO conversations (user_id, title, created_at, updated_at)
    SELECT user_id, 'Previous conversation', created_at, updated_at
    FROM legacy_users
    RETURNING id, user_id
)
UPDATE messages AS message
SET conversation_id = created.id
FROM created
WHERE message.user_id = created.user_id
  AND message.conversation_id IS NULL;

CREATE INDEX IF NOT EXISTS conversations_user_updated_idx
ON conversations (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS messages_conversation_idx
ON messages (conversation_id, id);
