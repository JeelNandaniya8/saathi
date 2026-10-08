ALTER TABLE exam_plans ADD COLUMN IF NOT EXISTS last_replan_token TEXT;
ALTER TABLE exam_plan_tasks ADD COLUMN IF NOT EXISTS last_replanned_at TIMESTAMPTZ;
