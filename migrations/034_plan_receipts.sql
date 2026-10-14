ALTER TABLE chat_action_receipts ADD COLUMN IF NOT EXISTS resource_ids BIGINT[];
-- Each existing plan was inserted atomically using the same transaction timestamp.
UPDATE chat_action_receipts r SET resource_ids=(
 SELECT array_agg(t.id ORDER BY t.id) FROM tasks t
 WHERE t.user_id=r.user_id AND t.created_at=(
  SELECT first_task.created_at FROM tasks first_task WHERE first_task.id=r.resource_id AND first_task.user_id=r.user_id
 )
) WHERE r.kind='plan' AND r.resource_ids IS NULL;
