ALTER TABLE care_occurrences ADD COLUMN IF NOT EXISTS title_snapshot TEXT;
ALTER TABLE care_occurrences ADD COLUMN IF NOT EXISTS instructions_snapshot TEXT;
-- This captures the available legacy text; it cannot reconstruct unknown prior edits.
UPDATE care_occurrences o SET title_snapshot=r.title,instructions_snapshot=r.note
FROM reminders r WHERE r.id=o.reminder_id AND o.title_snapshot IS NULL;
