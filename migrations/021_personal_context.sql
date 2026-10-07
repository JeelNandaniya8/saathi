CREATE SEQUENCE IF NOT EXISTS personal_context_revision;
CREATE TABLE IF NOT EXISTS personal_context_fields (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN ('care','study')),
    field TEXT NOT NULL,
    value TEXT NOT NULL CHECK (length(value) BETWEEN 1 AND 1500),
    source TEXT NOT NULL CHECK (source IN ('user_reported','user_entered_clinician_instruction')),
    use_in_ai BOOLEAN NOT NULL DEFAULT FALSE,
    version BIGINT NOT NULL DEFAULT nextval('personal_context_revision'),
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(user_id,category,field)
);
CREATE TABLE IF NOT EXISTS exam_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL,
    title TEXT NOT NULL,
    exam_date DATE NOT NULL,
    timezone TEXT NOT NULL,
    daily_minutes INTEGER NOT NULL CHECK (daily_minutes BETWEEN 10 AND 240),
    topics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id,client_id)
);
CREATE TABLE IF NOT EXISTS exam_plan_tasks (
    plan_id INTEGER NOT NULL REFERENCES exam_plans(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY(plan_id,task_id)
);
