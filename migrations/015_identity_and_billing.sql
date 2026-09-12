-- Add verified identities without treating legacy email-only sign-ins as verified.
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_subject TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS users_google_subject_unique ON users(google_subject) WHERE google_subject IS NOT NULL;
ALTER TABLE pending_verifications ADD COLUMN IF NOT EXISTS referred_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Deleting an inviter must not prevent account deletion for either person.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_referred_by_id_fkey;
ALTER TABLE users ADD CONSTRAINT users_referred_by_id_fkey FOREIGN KEY (referred_by_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS payment_orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    price_key TEXT NOT NULL,
    plan TEXT NOT NULL CHECK (plan IN ('plus','family')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    duration_days INTEGER NOT NULL CHECK (duration_days BETWEEN 1 AND 366),
    is_test BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL DEFAULT 'created',
    payment_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS payment_orders_user_idx ON payment_orders(user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS access_grants (
    source_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ends_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS access_grants_user_idx ON access_grants(user_id,ends_at);
CREATE TABLE IF NOT EXISTS payment_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS referral_rewards (
    referred_user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    referrer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (referred_user_id <> referrer_user_id)
);

-- Existing finite grants remain valid. Undated legacy upgrades require review.
INSERT INTO access_grants (source_id,user_id,plan,ends_at)
SELECT 'legacy:' || id,id,plan,subscription_end_at FROM users
WHERE plan IN ('plus','family') AND plan_status='active' AND subscription_end_at>NOW()
ON CONFLICT DO NOTHING;

-- Once only through the numbered runner: retire sessions issued by the old
-- email-only login path. Users sign in again using a verified method.
UPDATE users SET session_version=COALESCE(session_version,1)+1;
