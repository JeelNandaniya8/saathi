-- 012_subscriptions: Razorpay subscription tracking columns
-- Tracks external Razorpay subscription IDs and subscription expiration timestamps.
-- This migration is idempotent and safe to apply across production and test environments.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT,
  ADD COLUMN IF NOT EXISTS subscription_end_at TIMESTAMPTZ;
