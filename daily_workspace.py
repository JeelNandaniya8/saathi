"""Account-owned study organisation, review scheduling and everyday preferences."""
import re
from contextlib import contextmanager
from datetime import datetime,time,timedelta,timezone
from functools import wraps
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

import psycopg2
from psycopg2.extras import execute_values
from flask import jsonify,request

DEFAULTS={'goal':'explore','onboarding_done':False,'timezone':'UTC','quiet_enabled':False,
          'quiet_start':'22:00','quiet_end':'08:00','notification_mode':'immediate','digest_time':'18:00','celebrations':False}


def preferences(row=None):
    result=dict(DEFAULTS)
    for key in result:
        if row and row.get(key) is not None:
            value=row[key];result[key]=value.strftime('%H:%M') if isinstance(value,time) else value
    return result


def quiet_now(pref,now):
    pref=preferences(pref)
    if not pref['quiet_enabled']:return False
    local=now.astimezone(ZoneInfo(pref['timezone'])).strftime('%H:%M')
    start,end=pref['quiet_start'],pref['quiet_end']
    return start<=local<end if start<end else local>=start or local<end


def validated_preferences(data,current):
    if not isinstance(data,dict) or set(data)-set(DEFAULTS)-{'language'}:raise ValueError('Use the displayed preference controls.')
    result={**preferences(current),**{k:v for k,v in data.items() if k in DEFAULTS}}
    for key in ('onboarding_done','quiet_enabled','celebrations'):
        if type(result[key]) is not bool:raise ValueError('Choose a valid preference.')
    for key,allowed in [('goal',{'study','routines','wellbeing','explore'}),('notification_mode',{'immediate','digest'})]:
        if not isinstance(result[key],str) or result[key] not in allowed:raise ValueError('Choose a supported option.')
    zone=result['timezone']
    if not isinstance(zone,str) or len(zone)>80:raise ValueError('Choose a valid timezone.')
    try:ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError('Choose a valid timezone.') from None
    for key in ('quiet_start','quiet_end','digest_time'):
        if not isinstance(result[key],str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',result[key]):raise ValueError('Choose a valid time.')
    if result['quiet_enabled'] and result['quiet_start']==result['quiet_end']:raise ValueError('Quiet hours must have different start and end times.')
    if result['quiet_enabled'] and result['notification_mode']=='digest':
        start,end,digest=result['quiet_start'],result['quiet_end'],result['digest_time']
        if (start<=digest<end if start<end else digest>=start or digest<end):raise ValueError('Choose a summary time outside quiet hours.')
    language=data.get('language')
    if language is not None and (not isinstance(language,str) or language not in {'en','gu','hi'}):raise ValueError('Choose English, Gujarati or Hindi.')
    return result


def flashcards(text):
    block=re.search(r'\[FLASHCARDS\]([\s\S]*?)\[/FLASHCARDS\]',str(text),re.I)
    if not block:return []
    pattern=r'Front:\s*([\s\S]*?)\n\s*Back:\s*([\s\S]*?)(?=\n\s*---\s*\n|\n\s*Front:|$)'
    return [(front.strip()[:4000],back.strip()[:6000]) for front,back in re.findall(pattern,block[1],re.I) if front.strip() and back.strip()][:12]


def mock_revision_rows(uid,test_id,topic,review):
    return [(uid,test_id,item['id'],topic,item['question'],
             item['correct_answer']+': '+item['options'][item['correct_answer']]+'\n\n'+item['explanation'])
            for item in review if not item['is_correct']]


def insert_mock_revision(cur,rows):
    if rows:
        execute_values(cur,'''INSERT INTO revision_items(user_id,test_id,item_index,topic,front,back)
            VALUES %s ON CONFLICT(test_id,item_index) DO NOTHING''',rows,page_size=500)


def add_mock_revision(cur,uid,test_id,topic,review):
    insert_mock_revision(cur,mock_revision_rows(uid,test_id,topic,review))


def flash_revision_rows(uid,message_id,progress,content):
    cards=flashcards(content);rows=[]
    for index in progress.get('review_indices',[]):
        if type(index) is int and 0<=index<len(cards):
            rows.append((uid,message_id,index,'Saved flashcards',*cards[index]))
    return rows


def insert_flash_revision(cur,rows):
    if rows:
        execute_values(cur,'''INSERT INTO revision_items(user_id,message_id,item_index,topic,front,back)
            VALUES %s ON CONFLICT(message_id,item_index) DO NOTHING''',rows,page_size=500)


def add_flash_revision(cur,uid,message_id,progress):
    if not progress.get('review_indices'):return
    cur.execute("SELECT content FROM messages WHERE id=%s AND user_id=%s AND role='assistant'",(message_id,uid));message=cur.fetchone()
    if message:insert_flash_revision(cur,flash_revision_rows(uid,message_id,progress,message['content']))


def review_schedule(rating,repetitions,now):
    if rating=='again':return now+timedelta(minutes=10),0
    if rating=='hard':return now+timedelta(days=1),repetitions
    if rating!='good':raise ValueError('Choose Again, Hard or Got it.')
    days=(1,3,7,14,30)[min(repetitions,4)]
    return now+timedelta(days=days),min(repetitions+1,5)


# Identifiers below are fixed application-owned SQL, never supplied by a request.
RESOURCES={
    'conversation':('conversation_id','conversations','title'),
    'attachment':('attachment_id','chat_attachments','original_name'),
    'note':('note_id','quick_notes','title'),
    'test':('test_id','mock_tests','topic'),
    'mindmap':('mindmap_id','mindmaps','topic'),
}


def resource_sql(kind):
    if kind not in RESOURCES:raise ValueError('Choose a supported resource type.')
    column,table,title=RESOURCES[kind]
    return column,table,title


def moved_due(value,now,zone):
    local=value.astimezone(zone)
    tomorrow=now.astimezone(zone).date()+timedelta(days=1)
    return datetime.combine(tomorrow,local.time(),zone).astimezone(timezone.utc)


def register(app,b):
    @contextmanager
    def db():
        conn=b['get_db']();cur=conn.cursor()
        try:yield conn,cur
        except Exception:conn.rollback();raise
        finally:cur.close();conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            uid=b['require_user_id']()
            if not uid:return jsonify(error='Please log in first.'),401
            try:return fn(uid,*args,**kwargs)
            except ValueError as error:return jsonify(error=str(error)),400
            except psycopg2.errors.UniqueViolation:return jsonify(error='A space with this name already exists.'),409
        return wrapped

    @app.route('/api/workspace/preferences',methods=['GET','PATCH'])
    @private
    def workspace_preferences(uid):
        with db() as (conn,cur):
            cur.execute('SELECT language FROM users WHERE id=%s FOR UPDATE',(uid,));user=cur.fetchone()
            cur.execute('SELECT * FROM workspace_preferences WHERE user_id=%s',(uid,));saved=cur.fetchone()
            pref=preferences(saved)
            if request.method=='PATCH':
                data=request.get_json(silent=True);pref=validated_preferences(data,pref)
                cur.execute('''INSERT INTO workspace_preferences(user_id,goal,onboarding_done,timezone,quiet_enabled,quiet_start,quiet_end,notification_mode,digest_time,celebrations)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET
                    goal=EXCLUDED.goal,onboarding_done=EXCLUDED.onboarding_done,timezone=EXCLUDED.timezone,
                    quiet_enabled=EXCLUDED.quiet_enabled,quiet_start=EXCLUDED.quiet_start,quiet_end=EXCLUDED.quiet_end,
                    notification_mode=EXCLUDED.notification_mode,digest_time=EXCLUDED.digest_time,celebrations=EXCLUDED.celebrations,updated_at=NOW()''',
                    (uid,*(pref[key] for key in DEFAULTS)))
                if data.get('language'):
                    cur.execute('UPDATE users SET language=%s WHERE id=%s',(data['language'],uid));user['language']=data['language']
                conn.commit()
        return jsonify(preferences={**pref,'language':user['language']},in_quiet_hours=quiet_now(pref,datetime.now(timezone.utc)))

    @app.route('/api/subject-spaces',methods=['GET','POST'])
    @private
    def spaces(uid):
        with db() as (conn,cur):
            if request.method=='POST':
                data=request.get_json(silent=True)
                if not isinstance(data,dict) or not isinstance(data.get('name'),str) or not 1<=len(data['name'].strip())<=80:raise ValueError('Use a subject name of 1–80 characters.')
                color=data.get('color','blue')
                if not isinstance(color,str) or color not in {'blue','sage','violet','gold'}:raise ValueError('Choose a displayed colour.')
                cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
                cur.execute('SELECT count(*) AS n FROM subject_spaces WHERE user_id=%s',(uid,))
                if cur.fetchone()['n']>=30:raise ValueError('You can keep up to 30 subject spaces.')
                cur.execute('INSERT INTO subject_spaces(user_id,name,color) VALUES(%s,%s,%s) RETURNING id,name,color',(uid,data['name'].strip(),color));space=cur.fetchone();conn.commit()
                return jsonify(space=space),201
            cur.execute('''SELECT s.id,s.name,s.color,count(i.id) AS item_count FROM subject_spaces s
                LEFT JOIN subject_items i ON i.space_id=s.id AND i.user_id=s.user_id
                WHERE s.user_id=%s GROUP BY s.id ORDER BY s.name,s.id''',(uid,));rows=cur.fetchall()
        return jsonify(spaces=rows)

    @app.route('/api/subject-spaces/<int:space_id>',methods=['PATCH','DELETE'])
    @private
    def change_space(uid,space_id):
        with db() as (conn,cur):
            cur.execute('SELECT id FROM subject_spaces WHERE id=%s AND user_id=%s FOR UPDATE',(space_id,uid))
            if not cur.fetchone():return jsonify(error='Subject space not found.'),404
            if request.method=='DELETE':cur.execute('DELETE FROM subject_spaces WHERE id=%s AND user_id=%s',(space_id,uid))
            else:
                data=request.get_json(silent=True)
                if not isinstance(data,dict) or not isinstance(data.get('name'),str) or not 1<=len(data['name'].strip())<=80:raise ValueError('Use a subject name of 1–80 characters.')
                cur.execute('UPDATE subject_spaces SET name=%s WHERE id=%s AND user_id=%s',(data['name'].strip(),space_id,uid))
            conn.commit()
        return jsonify(ok=True)

    @app.get('/api/subject-resources')
    @private
    def available_resources(uid):
        kind=request.args.get('kind','note');_,table,title=resource_sql(kind)
        query=request.args.get('q','')[:100]
        try:offset=max(0,min(int(request.args.get('offset','0')),100000))
        except ValueError:raise ValueError('Choose a valid results page.') from None
        # psycopg Identifier quotes only identifiers from RESOURCES above.
        from psycopg2 import sql
        statement=sql.SQL('SELECT id,{} AS title FROM {} WHERE user_id=%s AND {} ILIKE %s ORDER BY id DESC LIMIT 51 OFFSET %s').format(sql.Identifier(title),sql.Identifier(table),sql.Identifier(title))
        with db() as (_,cur):cur.execute(statement,(uid,'%'+query+'%',offset));rows=cur.fetchall()
        return jsonify(resources=rows[:50],has_more=len(rows)>50,offset=offset,kind=kind)

    @app.route('/api/subject-spaces/<int:space_id>/items',methods=['GET','POST'])
    @private
    def space_items(uid,space_id):
        from psycopg2 import sql
        with db() as (conn,cur):
            cur.execute('SELECT id,name,color FROM subject_spaces WHERE id=%s AND user_id=%s FOR UPDATE',(space_id,uid));space=cur.fetchone()
            if not space:return jsonify(error='Subject space not found.'),404
            if request.method=='POST':
                data=request.get_json(silent=True)
                if not isinstance(data,dict) or not isinstance(data.get('kind'),str) or type(data.get('resource_id')) is not int:raise ValueError('Choose a saved resource.')
                column,table,_=resource_sql(data['kind'])
                cur.execute(sql.SQL('SELECT id FROM {} WHERE id=%s AND user_id=%s FOR KEY SHARE').format(sql.Identifier(table)),(data['resource_id'],uid))
                if not cur.fetchone():return jsonify(error='Saved resource not found.'),404
                cur.execute(sql.SQL('SELECT id FROM subject_items WHERE space_id=%s AND {}=%s').format(sql.Identifier(column)),(space_id,data['resource_id']))
                if cur.fetchone():return jsonify(ok=True)
                cur.execute('SELECT count(*) AS n FROM subject_items WHERE space_id=%s',(space_id,))
                if cur.fetchone()['n']>=300:raise ValueError('A subject space can contain up to 300 links.')
                cur.execute(sql.SQL('INSERT INTO subject_items(user_id,space_id,{}) VALUES(%s,%s,%s) ON CONFLICT(space_id,{}) DO NOTHING').format(sql.Identifier(column),sql.Identifier(column)),(uid,space_id,data['resource_id']));conn.commit()
                return jsonify(ok=True)
            rows=[]
            for kind,(column,table,title) in RESOURCES.items():
                cur.execute(sql.SQL('''SELECT i.id,r.id AS resource_id,r.{} AS title FROM subject_items i JOIN {} r ON r.id=i.{}
                    WHERE i.space_id=%s AND i.user_id=%s AND r.user_id=%s ORDER BY i.id DESC''').format(sql.Identifier(title),sql.Identifier(table),sql.Identifier(column)),(space_id,uid,uid))
                rows.extend({**row,'kind':kind} for row in cur.fetchall())
        return jsonify(space=space,items=rows)

    @app.delete('/api/subject-spaces/<int:space_id>/items/<int:item_id>')
    @private
    def unlink_item(uid,space_id,item_id):
        with db() as (conn,cur):
            cur.execute('DELETE FROM subject_items WHERE id=%s AND space_id=%s AND user_id=%s RETURNING id',(item_id,space_id,uid));removed=cur.fetchone();conn.commit()
        return (jsonify(ok=True),200) if removed else (jsonify(error='Link not found.'),404)

    @app.get('/api/revision')
    @private
    def revision_queue(uid):
        with db() as (_,cur):
            cur.execute('''SELECT id,topic,front,back,next_review_at,repetitions,version,test_id,message_id FROM revision_items
                WHERE user_id=%s AND paused=FALSE AND next_review_at<=NOW() ORDER BY next_review_at,id LIMIT 50''',(uid,));rows=cur.fetchall()
            cur.execute('''SELECT count(*) FILTER(WHERE next_review_at<=NOW()) AS due,count(*) FILTER(WHERE next_review_at>NOW()) AS upcoming,
                min(next_review_at) FILTER(WHERE next_review_at>NOW()) AS next_at FROM revision_items WHERE user_id=%s AND paused=FALSE''',(uid,));counts=cur.fetchone()
        return jsonify(items=[{**row,'next_review_at':row['next_review_at'].isoformat()} for row in rows],due=counts['due'],upcoming=counts['upcoming'],next_at=counts['next_at'].isoformat() if counts['next_at'] else None)

    @app.post('/api/revision/import')
    @private
    def import_revision(uid):
        import study_tools
        limit=b['limited']('revision_import',str(uid),5,5)
        if limit:return limit
        with db() as (conn,cur):
            cur.execute('''SELECT t.id,t.topic,t.questions_json,a.answers_json FROM mock_test_attempts a JOIN mock_tests t ON t.id=a.test_id
                WHERE a.user_id=%s AND t.user_id=%s ORDER BY a.created_at DESC LIMIT 100''',(uid,uid));tests=cur.fetchall()
            mock_rows=[]
            for test in tests:
                try:review=study_tools.grade(study_tools.validate_questions(test['questions_json']),test['answers_json'],0)['review']
                except ValueError:continue
                mock_rows.extend(mock_revision_rows(uid,test['id'],test['topic'],review))
            insert_mock_revision(cur,mock_rows)
            cur.execute('''SELECT p.message_id,p.progress,m.content FROM study_progress p JOIN messages m ON m.id=p.message_id
                WHERE p.user_id=%s AND m.user_id=%s AND p.kind='flashcards' AND m.role='assistant'
                ORDER BY p.updated_at DESC LIMIT 100''',(uid,uid));saved=cur.fetchall()
            flash_rows=[]
            for row in saved:flash_rows.extend(flash_revision_rows(uid,row['message_id'],row['progress'],row['content']))
            insert_flash_revision(cur,flash_rows)
            conn.commit()
        return jsonify(ok=True)

    @app.patch('/api/revision/<int:item_id>')
    @private
    def review_item(uid,item_id):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or type(data.get('version')) is not int:raise ValueError('Refresh this review card.')
        with db() as (conn,cur):
            cur.execute('SELECT * FROM revision_items WHERE id=%s AND user_id=%s FOR UPDATE',(item_id,uid));item=cur.fetchone()
            if not item:return jsonify(error='Review card not found.'),404
            if item['version']!=data['version']:return jsonify(error='This card was already reviewed or changed. Refresh the queue.'),409
            now=datetime.now(timezone.utc)
            if data.get('pause') is True:
                cur.execute('UPDATE revision_items SET paused=TRUE,version=version+1 WHERE id=%s',(item_id,));conn.commit();return jsonify(ok=True,paused=True)
            if item['paused'] or item['next_review_at']>now:return jsonify(error='This card is not due. Refresh the queue.'),409
            next_at,repetitions=review_schedule(data.get('rating'),item['repetitions'],now)
            cur.execute('UPDATE revision_items SET next_review_at=%s,repetitions=%s,version=version+1 WHERE id=%s',(next_at,repetitions,item_id));conn.commit()
        return jsonify(ok=True,next_review_at=next_at.isoformat())

    @app.get('/api/care/plan-preview')
    @private
    def care_plan_preview(uid):
        now=datetime.now(timezone.utc)
        with db() as (_,cur):
            cur.execute('SELECT * FROM workspace_preferences WHERE user_id=%s',(uid,));pref=preferences(cur.fetchone());zone=ZoneInfo(pref['timezone'])
            end=datetime.combine(now.astimezone(zone).date()+timedelta(days=1),time(),zone).astimezone(timezone.utc)
            cur.execute('''SELECT id,title,due_at,priority FROM tasks WHERE user_id=%s AND completed=FALSE AND priority<>'high'
                AND due_at<%s ORDER BY due_at,id LIMIT 30''',(uid,end));rows=cur.fetchall()
        return jsonify(tasks=[{**row,'due_at':row['due_at'].isoformat(),'proposed_at':moved_due(row['due_at'],now,zone).isoformat()} for row in rows],timezone=pref['timezone'])

    @app.post('/api/care/lighten-plan')
    @private
    def lighten_plan(uid):
        data=request.get_json(silent=True);items=data.get('items') if isinstance(data,dict) else None
        if not isinstance(items,list) or not 1<=len(items)<=30 or any(not isinstance(x,dict) or type(x.get('id')) is not int or not isinstance(x.get('due_at'),str) or not isinstance(x.get('proposed_at'),str) for x in items):raise ValueError('Select the tasks you want to move.')
        expected={x['id']:x for x in items}
        if len(expected)!=len(items):raise ValueError('Select each task once.')
        now=datetime.now(timezone.utc)
        with db() as (conn,cur):
            cur.execute('SELECT * FROM workspace_preferences WHERE user_id=%s',(uid,));pref=preferences(cur.fetchone());zone=ZoneInfo(pref['timezone'])
            end=datetime.combine(now.astimezone(zone).date()+timedelta(days=1),time(),zone).astimezone(timezone.utc)
            cur.execute('''SELECT id,due_at FROM tasks WHERE user_id=%s AND id=ANY(%s) AND completed=FALSE AND priority<>'high'
                AND due_at<%s ORDER BY id FOR UPDATE''',(uid,list(expected),end));rows=cur.fetchall()
            if len(rows)!=len(items) or any((expected[row['id']]['due_at']!=row['due_at'].isoformat() or expected[row['id']]['proposed_at']!=moved_due(row['due_at'],now,zone).isoformat()) for row in rows):
                return jsonify(error='A selected task changed. Review the current plan before applying changes.'),409
            for row in rows:cur.execute('UPDATE tasks SET due_at=%s,updated_at=NOW() WHERE id=%s AND user_id=%s',(moved_due(row['due_at'],now,zone),row['id'],uid))
            conn.commit()
        return jsonify(ok=True,moved=len(rows))
