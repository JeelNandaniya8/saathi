-- Page metadata and study progress stay attached to user-owned records.
-- The migration is additive and all dependent rows cascade with their owner.
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS file_only BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS source_pages JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE chat_attachments
ADD COLUMN IF NOT EXISTS page_count INTEGER;

ALTER TABLE chat_attachments
ADD COLUMN IF NOT EXISTS extracted_page_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS chat_attachment_pages (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attachment_id BIGINT NOT NULL REFERENCES chat_attachments(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (attachment_id, page_number)
);

CREATE INDEX IF NOT EXISTS chat_attachment_pages_user_attachment_idx
ON chat_attachment_pages (user_id, attachment_id, page_number);

CREATE TABLE IF NOT EXISTS study_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('quiz', 'flashcards')),
    progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS study_progress_user_updated_idx
ON study_progress (user_id, updated_at DESC);
