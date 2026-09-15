"""Optional wellbeing tools and reminders based only on the user's schedule."""
from contextlib import contextmanager
from datetime import datetime, timezone

from flask import jsonify, request

COPY = {
    'en': {
        'title':'Make space for yourself',
        'message':'You can take this one step at a time. Record what you have noticed and choose the support you need.',
        'explanation':'Symptoms can have many causes. Saathi cannot determine the cause, diagnose a condition or decide which treatment you need.',
        'steps': [('Write it down','Note when it started, what changed and how it affects your day.'),('Ask for support','Consider talking to someone you trust or a qualified health professional.'),('Prepare your questions','What should I watch for? What support is appropriate for me? When should I seek further help?')],
        'urgent':'If you think this is urgent or symptoms are severe or sudden, contact local emergency services or seek urgent medical care now.',
        'disclaimer':'These are general planning prompts, not an AI diagnosis or medical treatment. Follow your clinician’s advice. Saathi does not monitor emergencies.',
        'reminder':'Your scheduled reminder','scheduled':'You scheduled this reminder. Follow your saved instructions and any guidance from your clinician.',
        'ack':'Mark reminder complete','focus':'One next step','task':'A task you saved is ready when you are: ','planner':'Open planner',
        'hello':'A moment for you','checkin':'How is your day feeling? You can check in, write privately or talk things through.','chat':'Talk it through',
    },
    'gu': {
        'title':'તમારા માટે થોડો સમય',
        'message':'એક સમયે એક નાનું પગલું લો. તમે શું અનુભવો છો તે નોંધો અને જરૂરી મદદ પસંદ કરો.',
        'explanation':'લક્ષણોના ઘણા કારણો હોઈ શકે છે. સાથી કારણ નક્કી કરી શકતું નથી, નિદાન કરી શકતું નથી કે સારવાર પસંદ કરી શકતું નથી.',
        'steps':[('નોંધ કરો','તકલીફ ક્યારે શરૂ થઈ, શું બદલાયું અને દિવસ પર કેવી અસર પડે છે તે લખો.'),('મદદ માટે વાત કરો','વિશ્વાસપાત્ર વ્યક્તિ અથવા યોગ્ય આરોગ્ય નિષ્ણાત સાથે વાત કરવાનો વિચાર કરો.'),('પ્રશ્નો તૈયાર કરો','કયા ફેરફારો પર ધ્યાન આપવું? મારા માટે કઈ મદદ યોગ્ય છે? વધુ મદદ ક્યારે લેવી?')],
        'urgent':'તકલીફ તાત્કાલિક, ગંભીર કે અચાનક લાગે તો સ્થાનિક ઇમરજન્સી સેવા અથવા તાત્કાલિક તબીબી મદદ લો.',
        'disclaimer':'આ સામાન્ય તૈયારી માટેના મુદ્દા છે. નિદાન કે સારવાર નથી. તમારા ડોક્ટરની સલાહ અનુસરો. સાથી ઇમરજન્સીનું નિરીક્ષણ કરતું નથી.',
        'reminder':'તમારું નક્કી કરેલું રીમાઇન્ડર','scheduled':'આ રીમાઇન્ડર તમે નક્કી કર્યું છે. તમારી સેવ કરેલી સૂચના અને ડોક્ટરની સલાહ અનુસરો.',
        'ack':'રીમાઇન્ડર પૂર્ણ કરો','focus':'આગળનું એક પગલું','task':'તમે સેવ કરેલું એક કામ: ','planner':'યોજના ખોલો',
        'hello':'તમારા માટે એક ક્ષણ','checkin':'આજનો દિવસ કેવો લાગે છે? ચેક-ઇન કરો, ખાનગી નોંધ લખો અથવા વાત કરો.','chat':'વાત કરીએ',
    },
    'hi': {
        'title':'अपने लिए थोड़ा समय',
        'message':'एक समय में एक छोटा कदम लें। आप क्या महसूस कर रहे हैं उसे लिखें और ज़रूरी मदद चुनें।',
        'explanation':'लक्षणों के कई कारण हो सकते हैं। साथी कारण, निदान या आपके लिए सही उपचार तय नहीं कर सकता।',
        'steps':[('लिखकर रखें','तकलीफ कब शुरू हुई, क्या बदला और दिन पर क्या असर पड़ता है, लिखें।'),('मदद माँगें','किसी भरोसेमंद व्यक्ति या योग्य स्वास्थ्य पेशेवर से बात करने पर विचार करें।'),('सवाल तैयार करें','किन बदलावों पर ध्यान दूँ? मेरे लिए कौन सी मदद सही है? आगे मदद कब लेनी चाहिए?')],
        'urgent':'अगर स्थिति तुरंत मदद माँगती है या लक्षण गंभीर या अचानक हैं तो स्थानीय आपातकालीन सेवा या तुरंत चिकित्सा सहायता लें।',
        'disclaimer':'ये सामान्य तैयारी के सुझाव हैं। निदान या उपचार नहीं। अपने चिकित्सक की सलाह मानें। साथी आपातकाल की निगरानी नहीं करता।',
        'reminder':'आपका तय किया रिमाइंडर','scheduled':'यह रिमाइंडर आपने तय किया है। अपनी सेव की गई जानकारी और चिकित्सक की सलाह मानें।',
        'ack':'रिमाइंडर पूरा करें','focus':'अगला एक कदम','task':'आपका सेव किया एक काम: ','planner':'प्लानर खोलें',
        'hello':'आपके लिए एक पल','checkin':'आज का दिन कैसा लग रहा है? चेक-इन करें, निजी नोट लिखें या बात करें।','chat':'बात करें',
    },
}


def wellbeing_report(language):
    copy=COPY.get(language,COPY['en'])
    return {'comfort_title':copy['title'],'comfort_message':copy['message'],'body_explanation':copy['explanation'],
            'home_remedies':[{'icon':'','title':title,'tip':tip} for title,tip in copy['steps']],
            'medical_concepts':[],'red_flags':[copy['urgent']],'doctor_disclaimer':copy['disclaimer'],
            'generated_by_ai':False}


def register(app,b):
    @contextmanager
    def db():
        conn=b['get_db']();cur=conn.cursor()
        try:yield conn,cur
        except Exception:
            conn.rollback();raise
        finally:cur.close();conn.close()

    @app.post('/api/healer/consult')
    def wellbeing_consult():
        uid=b['require_user_id']()
        if not uid:return jsonify(error='Please log in first.'),401
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict) or not isinstance(data.get('symptoms'),str) or not 1<=len(data['symptoms'].strip())<=2000:
            return jsonify(error='Write a short note of up to 2,000 characters.'),400
        language=data.get('language','en')
        if not isinstance(language,str) or language not in COPY:return jsonify(error='Choose a supported language.'),400
        # This is an explicitly labelled preparation guide, never a fabricated
        # provider fallback. The private note is not stored or sent elsewhere.
        return jsonify(ok=True,report=wellbeing_report(language))

    @app.get('/api/care/nudge')
    def get_care_nudge():
        uid=b['require_user_id']()
        if not uid:return jsonify(error='Please log in first.'),401
        now=datetime.now(timezone.utc)
        with db() as (_,cur):
            cur.execute('SELECT language FROM users WHERE id=%s',(uid,));user=cur.fetchone()
            copy=COPY.get((user or {}).get('language'),COPY['en'])
            cur.execute('''SELECT id,title,note,next_run_at FROM reminders WHERE user_id=%s AND active=TRUE
                AND next_run_at<=%s ORDER BY next_run_at LIMIT 1''',(uid,now))
            reminder=cur.fetchone()
            if reminder:
                return jsonify(ok=True,nudge={'title':copy['reminder'],'message':reminder['title']+'. '+copy['scheduled'],
                    'scheduled_at':reminder['next_run_at'].isoformat(),'phase':'scheduled','sound_suggestion':None,
                    'action':{'type':'complete_reminder','reminder_id':reminder['id'],'scheduled_at':reminder['next_run_at'].isoformat(),'label':copy['ack']}})
            cur.execute('SELECT title FROM tasks WHERE user_id=%s AND completed=FALSE ORDER BY due_at ASC NULLS LAST,id LIMIT 1',(uid,))
            task=cur.fetchone()
        if task:
            return jsonify(ok=True,nudge={'title':copy['focus'],'message':copy['task']+task['title'],
                'phase':'focus','action':{'type':'planner','label':copy['planner']}})
        return jsonify(ok=True,nudge={'title':copy['hello'],'message':copy['checkin'],'phase':'checkin','action':{'type':'chat','label':copy['chat']}})

    @app.post('/api/reminders/<int:reminder_id>/ack')
    def reminder_quick_ack(reminder_id):
        uid=b['require_user_id']()
        if not uid:return jsonify(error='Please log in first.'),401
        data=request.get_json(silent=True) or {}
        expected=data.get('scheduled_at') if isinstance(data,dict) else None
        if not isinstance(expected,str):return jsonify(error='Refresh this reminder before marking it complete.'),400
        now=datetime.now(timezone.utc)
        with db() as (conn,cur):
            cur.execute('SELECT * FROM reminders WHERE id=%s AND user_id=%s FOR UPDATE',(reminder_id,uid));reminder=cur.fetchone()
            if not reminder:return jsonify(error='Reminder not found.'),404
            if not reminder['active'] or reminder['next_run_at'].isoformat()!=expected:
                return jsonify(ok=True,already_completed=True,reminder=b['reminder_to_dict'](reminder))
            if reminder['next_run_at']>now:return jsonify(error='This reminder is not due yet.'),409
            next_run,active=b['next_reminder_occurrence'](reminder['next_run_at'],reminder['recurrence'],now)
            cur.execute('UPDATE reminders SET next_run_at=%s,active=%s WHERE id=%s AND user_id=%s RETURNING *',(next_run,active,reminder_id,uid))
            updated=cur.fetchone();conn.commit()
        return jsonify(ok=True,reminder=b['reminder_to_dict'](updated))
