-- 012_subscriptions: Razorpay subscription tracking columns
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT,
  ADD COLUMN IF NOT EXISTS subscription_end_at TIMESTAMPTZ;
