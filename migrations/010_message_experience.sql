-- Saathi keeps experience metadata on the user-owned assistant message so it
-- remains visible after a conversation is reopened. Memory labels come only
-- from memories the user explicitly saved and can already inspect, pause or
-- delete. Feedback stores a small rating rather than copying conversation or
-- attachment content into a separate analytics table. Both changes are
-- additive and safe to run against an existing database.
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS memory_labels JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS feedback TEXT;
