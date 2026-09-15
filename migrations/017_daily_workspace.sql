CREATE TABLE IF NOT EXISTS workspace_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    goal TEXT NOT NULL DEFAULT 'explore' CHECK (goal IN ('study','routines','wellbeing','explore')),
    onboarding_done BOOLEAN NOT NULL DEFAULT FALSE,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    quiet_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    quiet_start TIME NOT NULL DEFAULT '22:00',
    quiet_end TIME NOT NULL DEFAULT '08:00',
    notification_mode TEXT NOT NULL DEFAULT 'immediate' CHECK (notification_mode IN ('immediate','digest')),
    digest_time TIME NOT NULL DEFAULT '18:00',
    celebrations BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS subject_spaces (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
    color TEXT NOT NULL DEFAULT 'blue' CHECK (color IN ('blue','sage','violet','gold')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id,name)
);
CREATE TABLE IF NOT EXISTS subject_items (
    id BIGSERIAL PRIMARY KEY,
    space_id BIGINT NOT NULL REFERENCES subject_spaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    attachment_id BIGINT REFERENCES chat_attachments(id) ON DELETE CASCADE,
    note_id BIGINT REFERENCES quick_notes(id) ON DELETE CASCADE,
    test_id BIGINT REFERENCES mock_tests(id) ON DELETE CASCADE,
    mindmap_id BIGINT REFERENCES mindmaps(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (num_nonnulls(conversation_id,attachment_id,note_id,test_id,mindmap_id)=1),
    UNIQUE(space_id,conversation_id),UNIQUE(space_id,attachment_id),UNIQUE(space_id,note_id),
    UNIQUE(space_id,test_id),UNIQUE(space_id,mindmap_id)
);
CREATE INDEX IF NOT EXISTS subject_items_owner ON subject_items(user_id,space_id);
CREATE TABLE IF NOT EXISTS revision_items (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id BIGINT REFERENCES mock_tests(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    item_index INTEGER NOT NULL,
    topic TEXT NOT NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    next_review_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    repetitions INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    paused BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (num_nonnulls(test_id,message_id)=1),
    UNIQUE(test_id,item_index),UNIQUE(message_id,item_index)
);
CREATE INDEX IF NOT EXISTS revision_due_owner ON revision_items(user_id,next_review_at) WHERE paused=FALSE;
CREATE TABLE IF NOT EXISTS push_digest_deliveries (
    id BIGSERIAL PRIMARY KEY,
    subscription_id BIGINT NOT NULL REFERENCES push_subscriptions(id) ON DELETE CASCADE,
    local_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    attempt_count INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    UNIQUE(subscription_id,local_date)
);
-- Evaluate each account's local clock before the delivery limit, so quiet accounts
-- cannot starve other users' notifications. This view contains no message content.
CREATE OR REPLACE VIEW workspace_alert_windows AS
SELECT u.id AS user_id,COALESCE(p.notification_mode,'immediate') AS notification_mode,
    clock.local_now::date AS local_date,
    clock.local_now::time>=COALESCE(p.digest_time,'18:00'::time) AS digest_due,
    NOT (COALESCE(p.quiet_enabled,FALSE) AND CASE WHEN p.quiet_start<p.quiet_end
        THEN clock.local_now::time>=p.quiet_start AND clock.local_now::time<p.quiet_end
        ELSE clock.local_now::time>=p.quiet_start OR clock.local_now::time<p.quiet_end END) AS allowed
FROM users u LEFT JOIN workspace_preferences p ON p.user_id=u.id
CROSS JOIN LATERAL (SELECT NOW() AT TIME ZONE COALESCE(p.timezone,'UTC') AS local_now) clock;
