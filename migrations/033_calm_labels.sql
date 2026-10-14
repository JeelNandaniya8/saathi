-- Normalize only labels produced by the old duplicate-fact extraction.
UPDATE memories SET label=CASE
 WHEN content ~* 'prefer.*(study|studying|learn)|(study|learning).*prefer' THEN 'Study preference'
 WHEN content ~* '\mprefer\M' THEN 'Preference'
 WHEN content ~* '\mexam\M' THEN 'Exam detail'
 ELSE 'Personal detail' END
WHERE label=left(content,60);

UPDATE reminders SET title=regexp_replace(title,'^do\s+','','i')
WHERE kind='general' AND title ~* '^do\s+\S';
