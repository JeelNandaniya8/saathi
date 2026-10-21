"""Turn-scoped intent hints. Stored text and uploaded files never grant access."""
import re


def command(text):
    text = str(text or '').strip()
    if not text or len(text) > 5000 or text.startswith(('>', '"', '“', '```')):
        return ''
    return text


def study_output(text):
    """Identify the requested study output, separately from workspace mutations."""
    text = command(text)
    converted = re.search(r'\b(?:turn|convert|transform)\b.+?\binto\s+(.+)', text, re.I | re.S)
    created = re.match(r'^(?:(?:please|can you|could you)\s+)*(?:make|create|generate|give|prepare)\s+(.+)', text, re.I | re.S)
    target = (converted or created)
    target = re.split(r'\b(?:from|using|about|for|on)\b|[.;\n]', target[1], maxsplit=1, flags=re.I)[0] if target else ''
    if re.search(r'\b(?:task|note|reminder|memory|habit|journal|plan|mind\s*map)\b', target, re.I):return None
    for pattern, mode in [(r'flash\s*cards?|ફ્લેશકાર્ડ|फ्लैशकार्ड', 'flashcards'), (r'\bquiz\b', 'quiz')]:
        if re.search(pattern, target, re.I):return mode
    if re.search(r'બનાવ|बनाओ', text) and re.search(r'ફ્લેશકાર્ડ|फ्लैशकार्ड', text):return 'flashcards'
    return None


def source_query(text):
    # A negative clause does not grant a one-reply exception to stored policy.
    return re.sub(r"\b(?:exclude|excluding|except|do not|don't|without|avoid|no)\b[^.;\n]*(?:[.;\n]|$)", '', command(text), flags=re.I)


SCHOOL_WORK = r'\b(?:assignments?|assigments?|aaisgments?|homework|coursework)\b|હોમવર્ક|ગૃહકાર્ય|(?:અ|એ)સ(?:ાઇ|ાઈ)ન્?મેન્ટ|હોમવક|असा[इई]न्?मेंट|होमवर्क|गृहकार्य'
CLASSROOM_SOURCE = r'classroom|ક્લાસરૂમ|क्लासरूम|' + SCHOOL_WORK
CLASSROOM_REFERENCE = r'\b(?:this|that|it|aa|e|ye)\b|આ(?:માં|નું|ની|ના|ને|\s)|તે(?:માં|નું|ની|ના|ને|\s)|इस|उस|यह|ये'


def classroom_text(text):
    # Apostrophes inside contractions are not quotation delimiters.
    text=re.sub(r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\x27[^\x27\n]+\x27(?!\w)|`[^`]*`', '', command(text))
    return text.replace('’', "'")


def classroom_denied(text):
    """A one-turn refusal overrides automatic sharing as well as explicit reads."""
    # A quoted source name still names a source: without "Classroom".
    text=command(text).replace('’', "'")
    if not re.search(CLASSROOM_SOURCE,text,re.I):return False
    # Negating a read is different from asking about work not submitted yet.
    if re.search(r'(?:બતાવ\S*|વાંચ\S*|તપાસ\S*|વાપર\S*)\s*(?:નહીં|નહિ|નથી)|(?:નહીં|નહિ|ન)\s*(?:બતાવ|વાંચ|તપાસ|વાપર)|(?:मत|नहीं|न)\s+(?:दिखा|बता|पढ़|जाँच|देख|भेज)|(?:दिखा\S*|बता\S*|पढ़\S*|जाँच\S*|देख\S*|भेज\S*)\s*(?:नहीं|मत)|\b(?:batav\w*|bata\w*|btao|vanch\w*|use|read|show)\s+(?:nahi|mat)\b|\b(?:nahi|mat)\s+(?:batav|bata|btao|vanch|use|read|show)',text,re.I):return True
    return bool(re.search(r"\b(?:do not|don't|without|avoid|exclude|excluding)\b[^.;\n]*(?:"+CLASSROOM_SOURCE+r')',text,re.I))


def excluded_sources(text):
    """Current-turn refusals override sharing; they never change saved policy."""
    text = command(text).replace('’', "'")
    patterns = {
        'tasks': r'\b(?:tasks?|planner|work)\b|કામ|कार्यसूची|काम',
        'reminders': r'\breminders?\b|રિમાઇન્ડર|रिमाइंडर',
        'classroom': CLASSROOM_SOURCE,
        'notes': r'\bnotes?\b|નોંધ|નોટ|नोट|टिप्पणी',
        'habits': r'\bhabits?\b|આદત|आदत',
        'study': r'\brevision\b|\bstudy\s+(?:sources?|data|materials?)\b|અભ્યાસ\s*સામગ્રી|अध्ययन\s*सामग्री',
        'exams': r'\bexams?\b|પરીક્ષા|परीक्षा',
        'memories': r'\bmemor(?:y|ies)\b|મેમરી|યાદો|स्मृत|यादें',
        'profile': r'\bprofile\b|પ્રોફાઇલ|प्रोफ़ाइल|प्रोफाइल',
    }
    denied = set()
    for clause in re.split(r'[.;\n।]', text):
        negative = re.search(r"\b(do not|don't|without|avoid|exclude|excluding)\b(.*)", clause, re.I)
        if negative:
            scope = re.split(r'\b(?:but|instead|then)\b', negative[2], maxsplit=1, flags=re.I)[0]
            # A task-date selector is a filter, not refusal of the Planner.
            if negative[1].lower() in {'exclude', 'excluding'} and re.match(r'\s*(?:tasks?|work)\s+from\s+(?:\d{4}-\d{2}-\d{2}\b|yesterday\b|today\b|tomorrow\b)', scope, re.I):
                continue
        elif re.search(r'(?:વાપર\S*|વાંચ\S*|તપાસ\S*|ઉપયોગ)\s*(?:નહીં|નહિ|નથી)|(?:નહીં|નહિ|ન)\s*(?:વાપર|વાંચ|તપાસ)|(?:मत|नहीं)\s+(?:पढ़|देख|भेज|दिखा|इस्तेमाल|उपयोग)|(?:इस्तेमाल|उपयोग|पढ़\S*|देख\S*)\s+(?:मत|नहीं)', clause, re.I):
            scope = clause
        else:
            continue
        if re.search(r'\bworkspace\b|\b(?:all|any)\s+(?:my\s+)?(?:saved\s+|personal\s+)?(?:sources|context|data)\b|\bpersonal context\b|કાર્યક્ષેત્ર|कार्य(?:क्षेत्र|स्थल)', scope, re.I):
            denied.update(patterns)
        else:
            denied.update(key for key, pattern in patterns.items() if re.search(pattern, scope, re.I))
    if classroom_denied(text):
        denied.add('classroom')
    return denied


def classroom_scope(text):
    """Quotes and a refusal to use school data cannot grant source access."""
    if 'classroom' in excluded_sources(text):return ''
    text=classroom_text(text)
    text=source_query(text)
    text=re.split(r'\b(?:title|content|details)\s*:',text,maxsplit=1,flags=re.I)[0]
    return text


def classroom_referential(text):
    """Only a generic reference may inherit a previous title, never a new topic."""
    scope=classroom_scope(text)
    if not re.search(CLASSROOM_REFERENCE,scope,re.I) or re.search(r'["“”‘’`\d]',scope):return False
    scope=re.sub(SCHOOL_WORK,' ',scope,flags=re.I)
    scope=re.sub(r'\b(?:what|do|i|have|need|to|should|in|on|for|this|that|it|the|my|is|are|about|inside|read|show|me|explain|tell|please|can|you|instructions?|description|requirements?|details?|content|mari|mara|maru|mare|aa|e|ma|shu|su|che|chhe|seni|karvanu|karvu|enu|ni|na|nu|kya|karna|hai|ye|isme)\b|આમાં|તેમાં|આ|તે|માં|ની|નું|ના|મારા|મારી|શું|છે|કરવાનું|કરવું|વિગતો|સૂચનાઓ|સમજાવો|इसमें|उसमें|इस|उस|यह|ये|के|की|का|में|क्या|करना|है|निर्देश|विवरण|दिखाओ|समझाओ',' ',scope,flags=re.I)
    return not re.search(r'\w',scope)


def classroom_detail(text, contextual=False):
    """A request to read requirements, not to generate a completed submission."""
    if explicit(text) or study_output(text):return ''
    scope=classroom_scope(text)
    if not scope or re.match(r'^(?:example\b|for example\b|hypothetical\b|pretend\b|quoted\b|ઉદાહરણ|उदाहरण)',scope,re.I):return ''
    if re.search(r'\b(?:sentence|phrase|meaning|translate|command)\b|વાક્ય|અર્થ|वाक्य|मतलब|अर्थ',scope,re.I):return ''
    if re.fullmatch(r'\s*(?:what (?:is|are) (?:an? |the )?(?:assignments?|homework)|(?:'+SCHOOL_WORK+r')\s+(?:su|shu|શું|kya|क्या)\s+(?:che|chhe|hoy|છે|hai|hota hai|है|होता है))[?.!\s]*',scope,re.I):return ''
    detail=re.search(r"\b(?:instructions?|description|requirements?|details?|content|explain)\b|\bwhat(?: exactly)?(?:['’]s| is)\s+(?:in|inside)\b|\bwhat\s+(?:do|should|must)\s+i\b.*\bdo\b|\bwhat\b.+?\b(?:about|contain\w*)\b|\b(?:su|shu|kya)\s+kar\w*\b|સૂચના|વિગત|વર્ણન|શું.*કર|સમજાવ|निर्देश|विवरण|क्या.*कर|समझा",scope,re.I)
    status=re.search(r'\b(?:pending|overdue|due|left|remaining|baki|ketla|ketli|kitne|kitna)\b|બાકી|કેટલ|बाकी|लंबित|कितन',scope,re.I)
    if not status and re.search(r'\b(?:su|shu|kya)\s+(?:che|chhe|hai)\b|શું.*છે|क्या.*है',scope,re.I):detail=True
    if not detail:return ''
    school=bool(re.search(SCHOOL_WORK,scope,re.I))
    # A literal quoted title may select an assignment. A quoted *request*
    # (Explain "What assignments are pending?") never grants source access.
    for match in re.finditer(r'"([^"\n]+)"|“([^”\n]+)”|‘([^’\n]+)’|(?<!\w)\x27([^\x27\n]+)\x27(?!\w)|`([^`]+)`',command(text)):
        title=next(group for group in match.groups() if group is not None)
        if re.search(SCHOOL_WORK,title,re.I) and not re.search(r'\b(?:what|which|show|list|read|check|pending|explain|shu|su|kya|baki)\b|શું|બતાવ|વાંચ|બાકી|क्या|दिखा|पढ़|बाकी',title,re.I):school=True
    return command(text) if school or contextual and classroom_referential(text) else ''


def classroom_read(text):
    """Only the current student's school-work question grants this read."""
    if explicit(text) or study_output(text):return ''
    if classroom_detail(text):return command(text)
    text = classroom_scope(text)
    if not text:return ''
    if re.match(r'^(?:example\b|for example\b|hypothetical\b|pretend\b|quoted\b|ઉદાહરણ|उदाहरण)',text,re.I):return ''
    # Quoted commands, literal titles and instructional questions are not reads.
    if re.search(r'\bhow (?:do|can|to)|explain how|કેવી રીતે|कैसे',text,re.I):return ''
    if re.fullmatch(r'\s*what (?:is|are) (?:an? |the )?(?:assignments?|homework|classroom)[?.!\s]*',text,re.I):return ''
    if re.fullmatch(r'\s*(?:'+SCHOOL_WORK+r')\s+(?:su|shu|શું|kya|क्या)\s+(?:che|chhe|hoy|છે|hai|hota hai|है|होता है)[?.!\s]*',text,re.I):return ''
    bare = re.fullmatch(r"\s*(?:what(?: is|'s|’s) pending|show (?:my )?pending work)[?.!\s]*",text,re.I)
    school = re.search(SCHOOL_WORK+r'|\b(?:school (?:(?:ni|ki|ka|ke) )?(?:tasks?|work|to[ -]?do list)|to[ -]?do list (?:from |for )?(?:my )?school)\b',text,re.I)
    classroom = re.search(r'classroom|ક્લાસરૂમ|क्लासरूम',text,re.I) and re.search(r'work|tasks?|assign|pending|due|left|remaining|કામ|બાકી|काम|बाकी',text,re.I)
    read = re.search(r'\b(?:what|which|show|list|read|check|pending|overdue|due|left|remaining|do i have|any|su|shu|kaya|kayu|ketla|ketli|ketlu|kya|kitna|kitne|batao|btao)\b|શું|કય|કેટલ|બતાવ|બાકી|shu|baki|batav|क्या|कौन|कितन|दिखा|बता|बाकी|लंबित',text,re.I)
    # A short owned noun phrase ("my classroom assignments") asks for a list;
    # ownership inside an essay/help request does not grant source access.
    owner = r'(?:my|mara|maru|mari|mare|mera|mere|meri|મારાં|મારું|મારા|મારી|મારે|मेरा|मेरे|मेरी)'
    school_name = r'(?:(?:google|ગૂગલ|गूगल)\s+)?(?:classroom|school|college|ક્લાસરૂમ|શાળા|કોલેજ|क्लासरूम|स्कूल|कॉलेज)(?:નાં|ના|ની|નું)?'
    owned = re.fullmatch(r'\s*'+owner+r'\s+(?:'+school_name+r'\s+(?:(?:na|ni|nu|ke|ki|ka|નાં|ના|ની|નું|का|के|की)\s+)?)?(?:'+SCHOOL_WORK+r')[?.!\s]*',text,re.I)
    return text.strip() if bare or owned or (read and (school or classroom)) else ''


def classroom_request(messages):
    """Resolve a short follow-up from user turns, never from assistant prose."""
    if not messages or messages[-1].get('attachments'):return {}
    text=command(messages[-1].get('content'))
    query=classroom_read(text);detail=bool(classroom_detail(text));reference=''
    if len(messages)>=3 and messages[-2].get('role')=='assistant' and messages[-3].get('role')=='user' and not messages[-3].get('attachments'):
        previous=messages[-3].get('content','')
        if classroom_read(previous):reference=previous
    if not query and reference and classroom_detail(text,contextual=True):query=text;detail=True
    if not query:return {}
    return dict(classroom_query=query,classroom_detail=detail,classroom_reference=reference if detail else '')


def classroom_definition(text):
    """Explaining a quoted read command does not inspect connection state."""
    text=command(text)
    if classroom_read(text):return False
    if not re.search(r'\bexplain\b|\bmeaning\b|\bwhat does\b|વાક્ય.*(?:અર્થ|સમજાવ)|वाक्य.*(?:मतलब|अर्थ|समझा)',text,re.I):return False
    quotes=re.finditer(r'"([^"\n]+)"|“([^”\n]+)”|‘([^’\n]+)’|(?<!\w)\x27([^\x27\n]+)\x27(?!\w)|`([^`]+)`',text)
    return any(classroom_read(next(group for group in match.groups() if group is not None)) for match in quotes)


def mode(text, selected='normal'):
    text = command(text)
    study = study_output(text)
    if study:return study
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
    text = full_text = command(text)
    # Literal field values are data, not permission to operate another feature.
    text=re.split(r'\b(?:title|content|details)\s*:|\b(?:titled|named|called)\s+',text,maxsplit=1,flags=re.I)[0]
    if not text or re.search(r'^(?:example\b|for example\b|here is an example\b|hypothetical\b|pretend\b|quoted\b|ઉદાહરણ|उदाहरण)', text, re.I):
        return False
    if study_output(text):return False
    if re.search(r'\bhow (?:do|can|to)|explain how|કેવી રીતે|कैसे',text,re.I):
        return False
    if re.search(r'\bpreview\b|\bdraft\b|review before|do not save|don.t save|without saving|પૂર્વાવલોકન|अभी सेव मत',text,re.I):
        return False
    if kind == 'mindmap' and operation == 'create':
        positive = source_query(text).strip()
        if positive != text:
            if re.search(r'\bpreview\b|\bdraft\b|review before|do not save|don.t save|without saving|પૂર્વાવલોકન|अभी सेव मत', full_text, re.I):
                return False
            return automatic(positive, kind, operation)
    mutations={'pause':r'\bpause\b|રોક|रोक', 'resume':r'\bresume\b|ફરી ચાલુ|फिर चालू',
               'snooze':r'\bsnooze\b|મોકૂફ|સ્નૂઝ|स्नूज़',
               'complete':r'\b(?:done|complete|completed|finished)\b|પૂર્ણ|પૂરું|पूरा',
               'edit':r'\b(?:edit|update|change|replace|rename|reschedule)\b|ફેરફાર|બદલ|बदल'}
    if operation in mutations and not re.search(mutations[operation],text,re.I):return False
    if operation=='create' and re.search(r'^(?:please\s+|can you\s+|could you\s+|yes[, ]+)*(?:pause|resume|snooze|mark|edit|update|change|replace|reschedule|delete|confirm)\b',text,re.I):return False
    if operation == 'delete' and not re.search(r'^(?:yes[, ]+delete|confirm.*delet|હા.*કાઢ|हाँ.*हटा)', text, re.I):
        return False
    if kind == 'memory' and re.search(r'^(?:my birthday is\b|i live in\b|મારો જન્મદિવસ|હું.*રહું|मेरा जन्मदिन|मैं.*रहता|मैं.*रहती)', text, re.I):
        return operation == 'create'
    verbs = r'^(?:(?:please|can you|could you|will you|i want you to|yes[, ]*|so[, ]*|okay[, ]*)\s*)*(?:save|remember|remind|add|create|make|put|turn|mark|snooze|pause|resume|edit|update|replace|change|reschedule|delete|confirm)\b|સાચવ|યાદ રાખ|યાદ કરાવ|ઉમેર|બનાવ|પૂર્ણ|મોકૂફ|રોક|ફેરફાર|કાઢ|सेव|याद रख|याद दिला|जोड़|बनाओ|पूरा|स्नूज़|रोक|बदल|हटा'
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
    denied = excluded_sources(text)
    classroom = classroom_read(text)
    classroom_text = classroom_scope(text)
    text = source_query(text)
    if not classroom and re.search(r'\bhow (?:do|can|to)|explain how|કેવી રીતે|कैसे|what (?:is|are) (?:a |the )?(?:note|task|reminder|classroom)\b',text,re.I):return set()
    if not re.search(r'\b(what|how much|show|list|read|use|summari[sz]e|make|turn|generate|left|remaining|mark|snooze|pause|resume|edit|update|replace|reschedule|delete|confirm)\b|કેટલ|બાકી|બતાવ|વાંચ|સારાંશ|બનાવ|રોક|પૂર્ણ|ફેરફાર|કાઢ|क्या|कितना|बाकी|दिखा|पढ़|सारांश|बनाओ|रोक|पूरा|बदल|हटा', text, re.I):
        return {'classroom'} - denied if classroom else set()
    patterns = {'tasks':r'\b(?:work|tasks?|planner|my plan)\b|કામ|મારી.*યોજના|काम|मेरी.*योजना',
                'reminders':r'\bremind(?:er)?s?\b|રિમાઇન્ડર|યાદ કરાવ|रिमाइंडर',
                'classroom':r'classroom|ક્લાસરૂમ|क्लासरूम',
                'notes':r'\b(?:read|use|show|what|summari[sz]e|edit|update|replace|reschedule|delete|confirm).*\bnotes?\b|\b(?:make|turn|generate).*\b(?:from|of|using) (?:my |the )?notes\b|(?:વાંચ|બતાવ|સારાંશ|ફેરફાર|કાઢ).*નોંધ|નોંધ.*(?:વાંચ|બતાવ|સારાંશ|ફેરફાર|કાઢ)|(?:पढ़|दिखा|सारांश|बदल|हटा).*नोट|नोट.*(?:पढ़|दिखा|सारांश|बदल|हटा)',
                'habits':r'habit|activity|આદત|પ્રવૃત્તિ|आदत|गतिविधि',
                'exams':r'exam|પરીક્ષા|परीक्षा', 'memories':r'memor|remember|birthday|home city|address|યાદ|जन्मदिन|याद'}
    result = {key for key, pattern in patterns.items() if re.search(pattern, classroom_text if key=='classroom' else text, re.I)}
    if classroom:result.add('classroom')
    if any(automatic(text,'task',op) for op in ('edit','complete','delete')):result.add('tasks')
    if re.search(r'\b(?:what|how much|show|list).*(?:remain|left|due|pending).*\btoday\b|(?:આજ|आज).*(?:બાકી|बाकी)',text,re.I):result.add('tasks')
    if re.search(r'activity today|આજ.*પ્રવૃત્તિ|आज.*गतिविधि', text, re.I):
        result.update(('tasks', 'reminders', 'habits'))
    return result - denied


def continuation(recent, answer):
    """An answer to the immediately preceding clarification inherits its scope."""
    answer=command(answer)
    if not answer or re.search(r'^(?:no(?: thanks)?[.!]?$|cancel\b|stop\b|never ?mind\b|not now\b|ના[.!]?$|नहीं[.!]?$|रद्द)',answer,re.I):return ''
    if explicit(answer):return ''
    if study_output(answer) or re.match(r'^(?:(?:please|can you|could you)\s+)*(?:turn|convert|transform|make|create|generate|give|prepare|show|list|read|use|explain|summari[sz]e|what|why|how)\b',answer,re.I):return ''
    if len(recent)<2 or recent[-1].get('role')!='assistant' or recent[-2].get('role')!='user':return ''
    question=str(recent[-1].get('content',''))
    question=re.sub(r'(?<=\?)\s+(?:For example|Example:|Include |જેમ કે|उदाहरण).*$', '', question, flags=re.I|re.S)
    if '<SAATHI_ACTION>' in question or not clarification(question):return ''
    return command(recent[-2].get('content'))


def explicit(text):
    return any(automatic(text,k,op) for k in ('task','reminder','note','memory','habit','journal','checkin','plan','mindmap') for op in ('create','edit','pause','resume','snooze','complete','delete'))


def clarification(text):
    text=str(text or '').strip().lstrip('*# ')
    return bool(len(text)<=500 and text.endswith('?') and not re.search(r'[.!?\n।。]',text[:-1]) and re.match(r'(?:(?:sure|okay)[, ]+)?(?:which|what|when|where|how much|how many|how long|can you|could you|would you|do you|please|કય|શું|કેટલ|ક્યારે|ક્યાં|કૃપા|कौन|क्या|कितन|कब|कहाँ|कृपया)',text,re.I) and not re.search(r'\b(?:saved|created|added|updated|deleted|paused|resumed|snoozed|scheduled|stored|recorded|ready|set|done|complete|completed|success)\b|સાચવ્યું|સાચવાય|બનાવ્યું|થઈ ગયું|सेव कर|सहेज|बना दिया|हो गया',text,re.I))
