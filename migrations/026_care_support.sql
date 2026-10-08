CREATE TABLE IF NOT EXISTS food_plans (
 id BIGSERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 client_id UUID NOT NULL,inputs JSONB NOT NULL,preview JSONB NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),UNIQUE(user_id,client_id)
);
CREATE TABLE IF NOT EXISTS care_shares (
 id BIGSERIAL PRIMARY KEY,owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,routine_ids JSONB NOT NULL,fields JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','revoked')),
 expires_at TIMESTAMPTZ NOT NULL,version INTEGER NOT NULL DEFAULT 1,CHECK(owner_id<>recipient_id),UNIQUE(owner_id,recipient_id)
);
CREATE INDEX IF NOT EXISTS care_shares_recipient ON care_shares(recipient_id,status,expires_at);
CREATE INDEX IF NOT EXISTS medication_due_idx ON reminders(current_scheduled_for,id) WHERE kind='medication' AND active=TRUE AND recurrence!='once';
