ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS tasks_completion_owner ON tasks(user_id,completed_at) WHERE completed=TRUE;
CREATE OR REPLACE FUNCTION saathi_task_completed_at() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        IF NEW.completed THEN NEW.completed_at=CURRENT_TIMESTAMP; ELSE NEW.completed_at=NULL; END IF;
    ELSIF NEW.completed IS DISTINCT FROM OLD.completed THEN
        IF NEW.completed THEN NEW.completed_at=CURRENT_TIMESTAMP; ELSE NEW.completed_at=NULL; END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS task_completed_at ON tasks;
CREATE TRIGGER task_completed_at BEFORE INSERT OR UPDATE OF completed ON tasks
FOR EACH ROW EXECUTE FUNCTION saathi_task_completed_at();

CREATE TABLE IF NOT EXISTS response_timings (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_id UUID NOT NULL,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    first_text_ms INTEGER CHECK(first_text_ms BETWEEN 0 AND 300000),
    total_ms INTEGER NOT NULL CHECK(total_ms BETWEEN 0 AND 300000),
    outcome TEXT NOT NULL CHECK(outcome IN ('complete','cancelled','error')),
    error_code TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id,request_id),
    CHECK(first_text_ms IS NULL OR first_text_ms<=total_ms)
);
CREATE INDEX IF NOT EXISTS response_timings_owner ON response_timings(user_id,created_at DESC);
