-- 013_mock_tests: AI Mock Test Simulator and Attempts tracking
CREATE TABLE IF NOT EXISTS mock_tests (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    question_count INTEGER NOT NULL DEFAULT 10,
    time_limit_minutes INTEGER NOT NULL DEFAULT 15,
    questions_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mock_tests_user ON mock_tests(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS mock_test_attempts (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT NOT NULL REFERENCES mock_tests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    accuracy_percentage NUMERIC(5, 2) NOT NULL,
    time_taken_seconds INTEGER NOT NULL,
    answers_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mock_test_attempts_user ON mock_test_attempts(user_id, created_at DESC);
