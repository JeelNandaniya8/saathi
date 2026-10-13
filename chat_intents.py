"""Turn-scoped intent hints. Stored text and uploaded files never grant access."""
import re


def command(text):
    text = str(text or '').strip()
    if not text or len(text) > 5000 or text.startswith(('>', '"', '“', '```')):
        return ''
    return text


def mode(text, selected='normal'):
    text = command(text)
    fallback='normal' if sources(text) or any(automatic(text,k) for k in ('task','reminder','note','memory','habit','journal','checkin')) else selected
    if not re.search(r'\b(make|create|turn|generate|summari[sz]e|explain|give|prepare)\b|બનાવ|સારાંશ|સમજાવ|बनाओ|सारांश|समझाओ', text, re.I):
        return fallback
    for pattern, value in [(r'flash\s*cards?|ફ્લેશકાર્ડ|फ्लैशकार्ड', 'flashcards'),
                           (r'study plan|અભ્યાસ.*યોજના|पढ़ाई.*योजना', 'study_plan'),
                           (r'quiz|questions|પ્રશ્ન|प्रश्न', 'quiz'),
                           (r'summari[sz]e|summary|સારાંશ|सारांश', 'summarise')]:
        if re.search(pattern, text, re.I):
            return value
    return fallback


def automatic(text, kind, operation='create'):
    text = command(text)
    if not text or re.search(r'\b(?:example|hypothetical|pretend|quoted)\b|ઉદાહરણ|उदाहरण', text, re.I):
        return False
    if re.search(r'\bhow (?:do|can|to)|explain how|કેવી રીતે|कैसे',text,re.I):
        return False
    if re.search(r'\bpreview\b|\bdraft\b|review before|do not save|don.t save|without saving|પૂર્વાવલોકન|अभी सेव मत',text,re.I):
        return False
    mutations={'pause':r'\bpause\b|રોક|रोक', 'resume':r'\bresume\b|ફરી ચાલુ|फिर चालू',
               'snooze':r'\bsnooze\b|મોકૂફ|સ્નૂઝ|स्नूज़',
               'complete':r'\b(?:done|complete|completed|finished)\b|પૂર્ણ|પૂરું|पूरा',
               'edit':r'\b(?:edit|update|change|replace|rename)\b|ફેરફાર|બદલ|बदल'}
    if operation in mutations and not re.search(mutations[operation],text,re.I):return False
    if operation=='create' and re.search(r'^(?:please\s+|can you\s+|could you\s+|yes[, ]+)*(?:pause|resume|snooze|mark|edit|update|change|replace|delete|confirm)\b',text,re.I):return False
    if operation == 'delete' and not re.search(r'^(?:yes[, ]+delete|confirm.*delet|હા.*કાઢ|हाँ.*हटा)', text, re.I):
        return False
    if kind == 'memory' and re.search(r'^(?:my birthday is\b|i live in\b|મારો જન્મદિવસ|હું.*રહું|मेरा जन्मदिन|मैं.*रहता|मैं.*रहती)', text, re.I):
        return operation == 'create'
    verbs = r'^(?:(?:please|can you|could you|will you|i want you to|yes[, ]*|so[, ]*|okay[, ]*)\s*)*(?:save|remember|remind|add|create|make|put|turn|mark|snooze|pause|resume|edit|update|replace|change|delete|confirm)\b|સાચવ|યાદ રાખ|યાદ કરાવ|ઉમેર|બનાવ|પૂર્ણ|મોકૂફ|રોક|ફેરફાર|કાઢ|सेव|याद रख|याद दिला|जोड़|बनाओ|पूरा|स्नूज़|रोक|बदल|हटा'
    if not re.search(verbs, text, re.I):
        return False
    if kind == 'task' and operation == 'complete' and re.search(r'^(?:please\s+)?mark\s+.+\s+(?:as\s+)?(?:done|complete|completed|finished)[.!]?$',text,re.I):
        return True
    patterns = {'task':r'task|revision|plan|કામ|અભ્યાસ|યોજના|काम|योजना',
                'plan':r'study plan|અભ્યાસ.*યોજના|पढ़ाई.*योजना',
                'reminder':r'remind|reminder|યાદ કરાવ|રિમાઇન્ડર|યાદ અપાવ|रिमाइंडर|याद दिला',
                'note':r'note|નોંધ|नोट', 'memory':r'remember|memory|birthday|home city|address|યાદ રાખ|जन्मदिन|याद रख',
                'mindmap':r'mind\s*map|માઇન્ડ.*મેપ|माइंड.*मैप',
                'habit':r'habit|આદત|आदत', 'journal':r'journal|જર્નલ|जर्नल',
                'checkin':r'check.?in|ચેક.?ઇન|चेक.?इन'}
    return bool(re.search(patterns.get(kind, r'(?!)'), text, re.I))


def sources(text):
    text = command(text)
    if re.search(r'\bhow (?:do|can|to)|explain how|કેવી રીતે|कैसे|what (?:is|are) (?:a |the )?(?:note|task|reminder|classroom)\b',text,re.I):return set()
    if not re.search(r'\b(what|how much|show|list|read|use|summari[sz]e|make|turn|generate|left|remaining|mark|snooze|pause|resume|edit|update|replace|delete|confirm)\b|કેટલ|બાકી|બતાવ|વાંચ|સારાંશ|બનાવ|રોક|પૂર્ણ|ફેરફાર|કાઢ|क्या|कितना|बाकी|दिखा|पढ़|सारांश|बनाओ|रोक|पूरा|बदल|हटा', text, re.I):
        return set()
    patterns = {'tasks':r'work|task|plan|revision|કામ|યોજના|काम|योजना',
                'reminders':r'remind|રિમાઇન્ડર|યાદ કરાવ|रिमाइंडर',
                'classroom':r'classroom|ક્લાસરૂમ|क्लासरूम',
                'notes':r'\b(?:read|use|show|what|summari[sz]e|edit|update|replace|delete|confirm).*\bnotes?\b|\b(?:make|turn|generate).*\b(?:from|of|using) (?:my |the )?notes\b|(?:વાંચ|બતાવ|સારાંશ|ફેરફાર|કાઢ).*નોંધ|નોંધ.*(?:વાંચ|બતાવ|સારાંશ|ફેરફાર|કાઢ)|(?:पढ़|दिखा|सारांश|बदल|हटा).*नोट|नोट.*(?:पढ़|दिखा|सारांश|बदल|हटा)',
                'habits':r'habit|activity|આદત|પ્રવૃત્તિ|आदत|गतिविधि',
                'exams':r'exam|પરીક્ષા|परीक्षा', 'memories':r'memor|remember|birthday|home city|address|યાદ|जन्मदिन|याद'}
    result = {key for key, pattern in patterns.items() if re.search(pattern, text, re.I)}
    if re.search(r'\b(?:what|how much|show|list).*(?:remain|left|due|pending).*\btoday\b|(?:આજ|आज).*(?:બાકી|बाकी)',text,re.I):result.add('tasks')
    if re.search(r'activity today|આજ.*પ્રવૃત્તિ|आज.*गतिविधि', text, re.I):
        result.update(('tasks', 'reminders', 'habits'))
    return result


def continuation(recent, answer):
    """An answer to the immediately preceding clarification inherits its scope."""
    answer=command(answer)
    if not answer or re.search(r'^(?:no(?: thanks)?[.!]?$|cancel\b|stop\b|never ?mind\b|not now\b|ના[.!]?$|नहीं[.!]?$|रद्द)',answer,re.I):return ''
    if explicit(answer):return ''
    if len(recent)<2 or recent[-1].get('role')!='assistant' or recent[-2].get('role')!='user':return ''
    question=str(recent[-1].get('content',''))
    if '<SAATHI_ACTION>' in question or not re.search(r'\?|which|what time|કયો|કેટલા|कब|कौन',question,re.I):return ''
    return command(recent[-2].get('content'))


def explicit(text):
    return any(automatic(text,k,op) for k in ('task','reminder','note','memory','habit','journal','checkin','plan','mindmap') for op in ('create','edit','pause','resume','snooze','complete','delete'))


def clarification(text):
    text=str(text or '').strip().lstrip('*# ')
    return bool(len(text)<=500 and text.endswith('?') and not re.search(r'[.!?\n।。]',text[:-1]) and re.match(r'(?:(?:sure|okay)[, ]+)?(?:which|what|when|where|how much|how many|how long|can you|could you|would you|do you|please|કય|શું|કેટલ|ક્યારે|ક્યાં|કૃપા|कौन|क्या|कितन|कब|कहाँ|कृपया)',text,re.I) and not re.search(r'\b(?:saved|created|added|updated|deleted|paused|resumed|snoozed|scheduled|stored|recorded|ready|set|done|complete|completed|success)\b|સાચવ્યું|સાચવાય|બનાવ્યું|થઈ ગયું|सेव कर|सहेज|बना दिया|हो गया',text,re.I))
