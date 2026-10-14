UPDATE memories SET content=regexp_replace(content,'[.;!]\s*(please\s+)?save (this|that)( fact| preference)? to (my )?memory[.!]?\s*$','','i')
WHERE content~*'[.;!]\s*(please\s+)?save (this|that)( fact| preference)? to (my )?memory[.!]?\s*$';
UPDATE memories SET label=left('Preference: '||regexp_replace(content,'^I prefer\s+','','i'),60)
WHERE label='Preference' AND content~*'^I prefer\s+';
