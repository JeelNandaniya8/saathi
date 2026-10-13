ALTER TABLE chat_action_receipts DROP CONSTRAINT IF EXISTS chat_action_receipts_kind_check;
ALTER TABLE chat_action_receipts ADD CONSTRAINT chat_action_receipts_kind_check
 CHECK(kind IN ('task','reminder','note','memory','habit','journal','checkin','plan','mindmap'));
