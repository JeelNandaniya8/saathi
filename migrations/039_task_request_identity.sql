-- Old tasks retain NULL identities; only explicit retried creates are deduplicated.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS client_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS tasks_user_client_id_unique
    ON tasks(user_id, client_id) WHERE client_id IS NOT NULL;
