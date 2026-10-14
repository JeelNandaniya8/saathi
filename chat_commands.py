"""Literal account commands. No model calls and no authority from quoted content."""
import calendar
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import chat_intents

MONTHS = {name.lower(): n for n, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): n for n, name in enumerate(calendar.month_abbr) if name})


def fact(text):
    value = re.sub(r'^(?:please\s+)?remember\s+(?:that\s+)?|^(?:યાદ રાખો?|યાદ રાખજે)\s*(?:કે\s*)?|^(?:याद रख(?:ो|ें)?|याद रखना)\s*(?:कि\s*)?', '', text, flags=re.I)
    birthday = re.search(r'(?:my birthday is|મારો જન્મદિવસ|मेरा जन्मदिन)\s+(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)', value, re.I)
    if birthday and birthday[2].lower() in MONTHS:
        month, day = MONTHS[birthday[2].lower()], int(birthday[1])
        if 1 <= day <= calendar.monthrange(2000, month)[1]:
            return {'kind': 'memory', 'title': 'Birthday', 'text': f'Birthday: {day} {calendar.month_name[month]}'}
        return {'question':'Choose a valid birthday date.'}
    city = re.search(r'i live in\s+([^.!?\n]+)', value, re.I)
    if city:
        return {'kind': 'memory', 'title': 'Home city', 'text': 'Home city: ' + city[1].strip()}
    value = re.split(r'\s+(?:Save this personal fact|This is a demo audit fact)\b', value, flags=re.I)[0].strip(' .')
    if value:
        label='Study preference' if re.search(r'prefer.*(?:study|studying|learn)|(?:study|learning).*prefer',value,re.I) else 'Preference' if re.search(r'\bprefer\b',value,re.I) else 'Exam detail' if re.search(r'\bexam\b',value,re.I) else 'Personal detail'
        return {'kind': 'memory', 'title': label, 'text': value}


def note(text):
    fields=re.search(r'\btitle\s*:\s*(.+?)\s*[;\n.]\s*content\s*:\s*(.+)',text,re.I|re.S)
    if fields:return {'kind':'note','title':fields[1].strip(),'text':fields[2].strip()}
    named = re.match(r'^(?:please\s+)?(?:save|add|create|make|put)\s+(?:this\s+(?:as|in)\s+)?(?:a\s+)?(?:private\s+)?note(?:\s+titled|\s+named|\s+with (?:the )?title)\s+(.+)', text, re.I | re.S)
    if not named:
        return None
    value = named[1].strip()
    quoted = re.match(r'["“]([^"”]+)["”]\s*(?:[:—\-.,]|with (?:the )?(?:content|text)|containing)*\s*(.+)', value, re.I | re.S)
    split = re.match(r'(.+?)\s*(?:[.;]?\s+(?:with |and )?(?:the )?(?:content|text)\s*[:=]?\s+|[:\n]|\s+containing\s+)\s*(.+)', value, re.I | re.S)
    match = quoted or split
    if match:
        return {'kind': 'note', 'title': match[1].strip(' .'), 'text': match[2].strip()}
    return {'question': 'What text should I save in the note? Include the title and content.'}


def reminder(text, zone, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(zone))
    clock = re.search(r'\bat\s+(\d{1,2})(?::([0-5]\d))?\s*(a\.?m\.?|p\.?m\.?)?\b', text, re.I) or re.search(r'\b(\d{1,2})(?::([0-5]\d))?\s*(a\.?m\.?|p\.?m\.?)\b', text, re.I)
    if not clock:
        return {'question': 'Which date and time? For example: tomorrow at 7 PM.'}
    hour, minute = int(clock[1]), int(clock[2] or 0)
    ampm = (clock[3] or '').lower().replace('.', '')
    if hour > 23 or (ampm and not 1 <= hour <= 12):
        return {'question': 'Choose a valid time, including AM or PM.'}
    if not ampm and 1 <= hour <= 12:
        return {'question': 'Is that AM or PM? Please include the full reminder and time.'}
    if ampm:
        hour = hour % 12 + (12 if ampm == 'pm' else 0)
    day = now.date()
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    named_date = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+('+'|'.join(MONTHS)+r')(?:\s+(\d{4}))?\b',text,re.I)
    try:
        if date_match:
            day = datetime.strptime(date_match[1], '%Y-%m-%d').date()
        elif named_date:
            day=day.replace(year=int(named_date[3] or day.year),month=MONTHS[named_date[2].lower()],day=int(named_date[1]))
        elif re.search(r'\btomorrow\b|કાલે|कल', text, re.I):
            day += timedelta(days=1)
        when = datetime.combine(day, datetime.min.time(), now.tzinfo).replace(hour=hour, minute=minute)
    except ValueError:
        return {'question': 'Choose a valid date in YYYY-MM-DD format.'}
    recurrence = 'daily' if re.search(r'\bevery day\b|\bdaily\b|દરરોજ|रोज', text, re.I) else 'weekly' if re.search(r'\bweekly\b|\bevery week\b', text, re.I) else 'once'
    if when <= now:
        if recurrence != 'once':
            when += timedelta(days=7 if recurrence == 'weekly' else 1)
        else:
            return {'question': 'That time has passed in ' + zone + '. Which future date should I use?'}
    topic = re.split(r'\s+(?:to|about|for)\s+', text[clock.end():].strip(), maxsplit=1, flags=re.I)
    title = topic[-1].strip(' .')
    title = re.sub(r'^(?:today|tomorrow|every day|daily|weekly)\s*(?:to|about|for)?\s*', '', title, flags=re.I)
    title = re.sub(r'^(?:to|about|for)\s+', '', title, flags=re.I)
    title = re.sub(r'^do\s+', '', title, flags=re.I)
    if not title:
        before=re.search(r'\b(?:to|about|for)\s+(.+?)\s*$',text[:clock.start()],re.I)
        if before:title=before[1].strip()
    if not title:
        return {'question': 'What should the reminder say? Include it after the time.'}
    return {'kind': 'reminder', 'title': title, 'text': '', 'at': when.isoformat(), 'recurrence': recurrence,
            'confirm_time': when.strftime('%d %B %Y, %I:%M %p') + ' · ' + zone}


def task(text,zone,now=None):
    match=re.match(r'^(?:please\s+)?(?:add|create|save)\s+(?:a\s+)?task\b[. :]*\s*(.*)',text,re.I|re.S)
    if not match:return None
    value=match[1].strip()
    fields=dict((k.lower(),v.strip()) for k,v in re.findall(r'(?:^|[;\n])\s*(title|details|content|due|priority)\s*:\s*([^;\n]+)',value,re.I))
    if fields:
        title=fields.get('title','');details=fields.get('details',fields.get('content',''));due=fields.get('due');priority=fields.get('priority','medium').lower()
    else:
        value=re.sub(r'^(?:titled|called|named|to)\s+','',value,flags=re.I)
        parts=re.split(r'\s+(?:due\s*:?\s*|for\s+|on\s+)(?=today\b|tomorrow\b|\d{4}-)',value,maxsplit=1,flags=re.I)
        title=parts[0].strip(' .');details='';due=parts[1] if len(parts)>1 else None;priority='medium'
        if not due and re.search(r'\b(?:today|tomorrow)\b.*\bat\b',title,re.I):return {'question':'What is the task title and deadline? For example: Add a task titled Revise physics due tomorrow at 7 PM.'}
    if not title:return {'question':'What task should I save? Include its title and optional deadline.'}
    at=None
    if due:
        try:
            at=datetime.fromisoformat(due.replace('Z','+00:00'))
            if at.tzinfo is None:at=at.replace(tzinfo=ZoneInfo(zone))
            at=at.isoformat()
        except ValueError:
            schedule=reminder('Remind me '+due+' to '+title,zone,now)
            if 'question' in schedule:return schedule
            at=schedule['at']
    return dict(kind='task',title=title,text=details,at=at,priority=priority)


def parse(text, zone='Asia/Kolkata', now=None):
    text = chat_intents.command(text)
    if not text:
        return None
    literal_task=task(text,zone,now)
    if literal_task is not None:return literal_task
    if chat_intents.automatic(text, 'memory') and re.match(r'^(?:please\s+)?remember\b|^my birthday is\b|^i live in\b|^મારો જન્મદિવસ|^હું|^યાદ રાખ|^मेरा जन्मदिन|^मैं|^याद रख',text,re.I):
        return fact(text)
    if chat_intents.automatic(text, 'note'):
        return note(text)
    if chat_intents.automatic(text, 'reminder') and re.match(r'^(?:please\s+)?remind\s+me\b', text, re.I):
        return reminder(text, zone, now)
    return None
