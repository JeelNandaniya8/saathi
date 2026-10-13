"""Small source-backed explanations; never substitute these for an uploaded text."""
import re
import chat_intents

REFERENCES = {
 'newton': ('https://ncert.nic.in/textbook/pdf/keph104.pdf', {
  'en': 'Newton’s second law says that net force equals the rate of change of momentum; for constant mass in an inertial frame, F_net = ma. For the same mass, a larger net force produces a larger acceleration in the force’s direction.',
  'gu': 'ન્યૂટનનો બીજો નિયમ કહે છે કે પરિણામી બળ વેગમાનમાં ફેરફારના દર બરાબર છે; અચળ દળ અને જડત્વીય સંદર્ભતંત્ર માટે F_net = ma છે. સમાન દળ માટે વધુ પરિણામી બળ લાગતાં બળની દિશામાં વધુ પ્રવેગ થાય છે.',
  'hi': 'न्यूटन का दूसरा नियम कहता है कि परिणामी बल संवेग के परिवर्तन की दर के बराबर है; स्थिर द्रव्यमान और जड़त्वीय संदर्भ तंत्र के लिए F_net = ma है। समान द्रव्यमान पर अधिक परिणामी बल लगाने से बल की दिशा में अधिक त्वरण होता है।'}),
 'probability': ('https://ncert.nic.in/textbook/pdf/jemh114.pdf', {
  'en': 'For a finite sample space with equally likely outcomes, P(E) = number of favourable outcomes / total number of outcomes. For a fair six-sided die, P(even number) = 3/6 = 1/2; this counting formula cannot be used unchanged when outcomes have different chances.',
  'gu': 'મર્યાદિત નમૂના અવકાશમાં બધા પરિણામો સમાન સંભાવનાવાળા હોય ત્યારે P(E) = અનુકૂળ પરિણામોની સંખ્યા / કુલ પરિણામોની સંખ્યા છે. નિષ્પક્ષ છ બાજુના પાસામાં સમ સંખ્યા આવવાની સંભાવના 3/6 = 1/2 છે; પરિણામોની સંભાવના અલગ હોય તો આ ગણતરીનું સૂત્ર સીધું લાગુ પડતું નથી.',
  'hi': 'सीमित प्रतिदर्श समष्टि में सभी परिणाम समप्रायिक हों, तब P(E) = अनुकूल परिणामों की संख्या / कुल परिणामों की संख्या है। निष्पक्ष छह फलकों वाले पासे में सम संख्या की प्रायिकता 3/6 = 1/2 है; अलग-अलग संभावनाओं वाले परिणामों पर यह गिनती का सूत्र सीधे लागू नहीं होता।'})}


def short_study(messages, mode='normal'):
    if mode not in {'normal','explain'} or not messages:return False
    last=messages[-1]
    text=chat_intents.command(last.get('content'))
    return bool(text and len(text)<=300 and not last.get('attachments') and not chat_intents.explicit(text)
                and not chat_intents.sources(text) and not re.search(r'\b(?:my|this|that|above|previous)\b|માર|આને|આનો|मेरे|मेरा|इसे|इसका',text,re.I)
                and re.search(r'\bexplain\b|\bwhat is\b|સમજાવ|क्या है|समझा',text,re.I))


def answer(messages,language='en',mode='normal'):
    if not short_study(messages,mode):return None
    text=messages[-1]['content']
    if re.search(r'Gujarati|[\u0a80-\u0aff]',text,re.I) and not re.search(r'in English',text,re.I):language='gu'
    elif re.search(r'Hindi|[\u0900-\u097f]',text,re.I) and not re.search(r'in English',text,re.I):language='hi'
    # A supplied numerical exercise, derivation or comparison needs an actual answer.
    if re.search(r'\b(?:derive|compare|calculate|solve|why|proof)\b|\d\s*(?:kg|N\b|m/s)|શા માટે|સાબિત|गणना|(?:^|\s)क्यों(?:\s|[?।.]|$)',text,re.I):return None
    key='newton' if re.search(r'newton.*(?:second|2nd)|ન્યૂટન.*બીજ|न्यूटन.*दूसर',text,re.I) else 'probability' if re.search(r'(?:probability|સંભાવના|પ્રાયિકતા|प्रायिकता).*(?:formula|સૂત્ર|सूत्र)|(?:formula|સૂત્ર|सूत्र).*(?:probability|સંભાવના|प्रायिकता)',text,re.I) else None
    if not key:return None
    source,copy=REFERENCES[key]
    label={'en':'Study reference','gu':'અભ્યાસ સંદર્ભ','hi':'अध्ययन संदर्भ'}.get(language,'Study reference')
    return copy.get(language,copy['en'])+'\n\n['+label+' · NCERT]('+source+')'


def compact_payload(payload,messages,language,mode):
    if not short_study(messages,mode):return None
    return {'contents':[payload['contents'][-1]],
            'systemInstruction':{'parts':[{'text':'Give a short, accurate study explanation in '+{'en':'English','gu':'Gujarati','hi':'Hindi'}.get(language,'English')+'. Include assumptions next to formulas. Do not claim account access, live verification or saved actions.'}]},
            'generationConfig':{'maxOutputTokens':900,'temperature':0.3}}
