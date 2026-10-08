"""Selected-course, student read-only import. No model, roster or Classroom writes."""
import base64
import hashlib
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import urlencode, urlparse, quote

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import jsonify, request, session, redirect
from psycopg2.extras import Json

SCOPES = ('https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.coursework.me.readonly')
API = 'https://classroom.googleapis.com/v1/'
TOKEN = 'https://oauth2.googleapis.com/token'

class ProviderError(Exception):
    def __init__(self, code):self.code=code


def configuration():
    values = [os.environ.get(k,'') for k in ('CLASSROOM_CLIENT_ID','CLASSROOM_CLIENT_SECRET','CLASSROOM_REDIRECT_URI','CLASSROOM_TOKEN_KEY')]
    try:
        uri=urlparse(values[2]);Fernet(values[3].encode())
        valid=all(values) and uri.scheme=='https' and bool(uri.netloc) and not uri.username and not uri.query and not uri.fragment and uri.path=='/api/classroom/callback'
    except (ValueError,TypeError):valid=False
    return values if os.environ.get('CLASSROOM_ENABLED','').lower()=='true' and valid else None


def cipher():
    config=configuration()
    if not config:raise ProviderError('not_configured')
    return Fernet(config[3].encode())


def provider_json(method,url,**kwargs):
    try:
        r=requests.request(method,url,timeout=(5,10),allow_redirects=False,**kwargs)
        if r.status_code not in (200,201):
            raise ProviderError({400:'reconnect_required' if url==TOKEN else 'provider_unavailable',401:'reconnect_required',403:'permission_or_admin_block',429:'quota'}.get(r.status_code,'provider_unavailable'))
        data=r.json()
        if not isinstance(data,dict):raise ValueError()
        return data
    except (requests.RequestException,ValueError):raise ProviderError('provider_unavailable') from None


def access_token(encrypted):
    config=configuration()
    try:refresh=cipher().decrypt(encrypted.encode()).decode()
    except (InvalidToken,UnicodeError):raise ProviderError('reconnect_required') from None
    data=provider_json('POST',TOKEN,data={'client_id':config[0],'client_secret':config[1],
        'refresh_token':refresh,'grant_type':'refresh_token'})
    token=data.get('access_token')
    if not isinstance(token,str) or not token:raise ProviderError('reconnect_required')
    return token


def list_pages(token,path,key,params=None):
    params=dict(params or {},pageSize=100);items=[]
    for _ in range(5):
        data=provider_json('GET',API+path,headers={'Authorization':'Bearer '+token},params=params)
        rows=data.get(key,[])
        if not isinstance(rows,list) or any(not isinstance(x,dict) for x in rows):raise ProviderError('provider_unavailable')
        items.extend(rows)
        if not data.get('nextPageToken'):return items
        params['pageToken']=data['nextPageToken']
    # Never declare a partial snapshot complete or mark absent assignments deleted.
    raise ProviderError('too_many_items')


def safe_link(value):
    try:
        u=urlparse(value)
        return value if u.scheme=='https' and u.hostname=='classroom.google.com' and not u.username and not u.password and len(value)<=2000 else ''
    except (ValueError,TypeError):return ''


def assignment(row):
    external=row.get('id')
    if not isinstance(external,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',external):raise ProviderError('provider_unavailable')
    due=None;uncertain=False
    if row.get('dueDate') or row.get('dueTime'):
        try:
            d,t=row['dueDate'],row['dueTime']
            due=datetime(d['year'],d['month'],d['day'],t.get('hours',0),t.get('minutes',0),t.get('seconds',0),tzinfo=timezone.utc)
        except (KeyError,TypeError,ValueError,AttributeError):uncertain=True
    title=row.get('title','');description=row.get('description','')
    if not isinstance(title,str) or not isinstance(description,str):raise ProviderError('provider_unavailable')
    return external,title[:3000],description[:30000],safe_link(row.get('alternateLink','')),due,uncertain


def register(app,b):
    @contextmanager
    def db():
        conn=b['get_db']();cur=conn.cursor()
        try:yield conn,cur
        except Exception:conn.rollback();raise
        finally:cur.close();conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args,**kw):
            uid=b['require_user_id']()
            if not uid:return jsonify(error='Please log in first.'),401
            if request.method=='POST' or request.args.get('refresh')=='1':
                limit=b['limited']('classroom_'+fn.__name__,str(uid),12,5)
                if limit:return limit
            try:return fn(uid,*args,**kw)
            except ProviderError as e:return jsonify(error_code=e.code,error='Classroom could not complete this action. Your imported work is retained.'),503
            except ValueError as e:return jsonify(error=str(e)),400
        return wrapped

    def confirmed():
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or data.get('confirmed') is not True:raise ValueError('Confirm this Classroom action first.')
        return data

    @app.get('/api/classroom/status')
    @private
    def status(uid):
        with db() as (_,cur):
            cur.execute('SELECT selected_courses,last_sync,last_error,version FROM classroom_connections WHERE user_id=%s',(uid,));row=cur.fetchone()
        return jsonify(configured=bool(configuration()),connected=bool(row),connection=row)

    @app.post('/api/classroom/connect')
    @private
    def connect(uid):
        confirmed();config=configuration()
        if not config:raise ProviderError('not_configured')
        state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with db() as (conn,cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
            cur.execute('SELECT user_id FROM classroom_connections WHERE user_id=%s',(uid,))
            if cur.fetchone():raise ValueError('Disconnect the current Classroom account before connecting another.')
            cur.execute('''INSERT INTO classroom_oauth_requests(user_id,state_hash,verifier_cipher,session_version,expires_at)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET state_hash=EXCLUDED.state_hash,
                verifier_cipher=EXCLUDED.verifier_cipher,session_version=EXCLUDED.session_version,expires_at=EXCLUDED.expires_at''',
                (uid,hashlib.sha256(state.encode()).hexdigest(),cipher().encrypt(verifier.encode()).decode(),session.get('session_version'),datetime.now(timezone.utc)+timedelta(minutes=10)))
            conn.commit()
        return jsonify(url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':config[0],'redirect_uri':config[2],
            'response_type':'code','scope':' '.join(SCOPES),'access_type':'offline','prompt':'consent select_account',
            'state':state,'code_challenge':challenge,'code_challenge_method':'S256','include_granted_scopes':'false'}))

    @app.get('/api/classroom/callback')
    @private
    def callback(uid):
        config=configuration()
        if not config:raise ProviderError('not_configured')
        state=request.args.get('state','')
        if not 20<=len(state)<=200:raise ValueError('Restart Classroom connection.')
        with db() as (conn,cur):
            cur.execute('DELETE FROM classroom_oauth_requests WHERE user_id=%s AND state_hash=%s RETURNING *',(uid,hashlib.sha256(state.encode()).hexdigest()))
            pending=cur.fetchone();conn.commit()
        if not pending or pending['expires_at']<datetime.now(timezone.utc) or pending['session_version']!=session.get('session_version'):
            raise ValueError('This connection request expired. Start again.')
        if request.args.get('error'):return redirect('/dashboard#study')
        code=request.args.get('code','')
        if not code or len(code)>4096:raise ValueError('Restart Classroom connection.')
        try:verifier=cipher().decrypt(pending['verifier_cipher'].encode()).decode()
        except InvalidToken:raise ProviderError('reconnect_required') from None
        tokens=provider_json('POST',TOKEN,data={'client_id':config[0],'client_secret':config[1],'redirect_uri':config[2],
            'code':code,'code_verifier':verifier,'grant_type':'authorization_code'})
        if not set(SCOPES).issubset(set(str(tokens.get('scope','')).split())):raise ProviderError('permission_or_admin_block')
        refresh=tokens.get('refresh_token')
        if not isinstance(refresh,str) or not refresh:raise ProviderError('reconnect_required')
        with db() as (conn,cur):
            cur.execute('SELECT session_version FROM users WHERE id=%s FOR UPDATE',(uid,))
            user=cur.fetchone()
            if not user or user['session_version']!=pending['session_version']:raise ValueError('Sign in and reconnect Classroom.')
            cur.execute('INSERT INTO classroom_connections(user_id,refresh_cipher) VALUES(%s,%s) ON CONFLICT DO NOTHING',(uid,cipher().encrypt(refresh.encode()).decode()))
            conn.commit()
        return redirect('/dashboard#study')

    @app.get('/api/classroom/courses')
    @private
    def courses(uid):
        with db() as (conn,cur):
            cur.execute('SELECT * FROM classroom_connections WHERE user_id=%s FOR UPDATE',(uid,));row=cur.fetchone()
            if not row:raise ValueError('Connect Classroom first.')
            if request.args.get('refresh')!='1':
                return jsonify(courses=row['course_catalog'],selected=row['selected_courses'],version=row['version'])
            catalog=list_pages(access_token(row['refresh_cipher']),'courses','courses',{'studentId':'me','courseStates':'ACTIVE','fields':'courses(id,name),nextPageToken'})
            catalog=[{'id':r['id'],'name':str(r.get('name',''))[:500]} for r in catalog if isinstance(r.get('id'),str)]
            cur.execute('UPDATE classroom_connections SET course_catalog=%s WHERE user_id=%s',(Json(catalog),uid));conn.commit()
        return jsonify(courses=catalog,selected=row['selected_courses'],version=row['version'])

    @app.post('/api/classroom/select')
    @private
    def select(uid):
        data=confirmed();ids=data.get('courses')
        if not isinstance(ids,list) or len(ids)>3 or any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Choose up to three courses.')
        with db() as (conn,cur):
            cur.execute('SELECT * FROM classroom_connections WHERE user_id=%s FOR UPDATE',(uid,));row=cur.fetchone()
            if not row:raise ValueError('Connect Classroom first.')
            if type(data.get('version')) is not int or data['version']!=row['version']:return jsonify(error='Selection changed. Refresh.'),409
            if not set(ids).issubset({r['id'] for r in row['course_catalog']}):raise ValueError('Refresh your course list first.')
            cur.execute('UPDATE classroom_connections SET selected_courses=%s,version=version+1 WHERE user_id=%s',(Json(ids),uid));conn.commit()
        return jsonify(ok=True)

    @app.post('/api/classroom/sync')
    @private
    def sync(uid):
        confirmed()
        with db() as (conn,cur):
            cur.execute('SELECT * FROM classroom_connections WHERE user_id=%s FOR UPDATE',(uid,));row=cur.fetchone()
            if not row:raise ValueError('Connect Classroom first.')
            if not row['selected_courses']:raise ValueError('Select courses first.')
            if row['last_sync'] and datetime.now(timezone.utc)-row['last_sync']<timedelta(minutes=1):
                return jsonify(error='Sync just completed. Wait one minute before trying again.'),429
            try:
                token=access_token(row['refresh_cipher']);snapshots={}
                for cid in row['selected_courses']:
                    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',cid):raise ProviderError('provider_unavailable')
                    work=list_pages(token,'courses/'+quote(cid,safe='')+'/courseWork','courseWork',
                        {'courseWorkStates':'PUBLISHED','fields':'courseWork(id,title,description,alternateLink,dueDate,dueTime),nextPageToken'})
                    snapshots[cid]=[assignment(r) for r in work]
            except ProviderError as e:
                cur.execute('UPDATE classroom_connections SET last_error=%s WHERE user_id=%s',(e.code,uid));conn.commit();raise
            count=0
            for cid,items in snapshots.items():
                cur.execute('UPDATE classroom_assignments SET available=FALSE WHERE user_id=%s AND course_id=%s',(uid,cid))
                for external,title,note,url,due,uncertain in items:
                    cur.execute('''INSERT INTO classroom_assignments(user_id,course_id,external_id,title,instructions,original_url,due_at,deadline_uncertain)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,course_id,external_id) DO UPDATE SET
                        title=EXCLUDED.title,instructions=EXCLUDED.instructions,original_url=EXCLUDED.original_url,
                        due_at=EXCLUDED.due_at,deadline_uncertain=EXCLUDED.deadline_uncertain,available=TRUE,synced_at=NOW()''',
                        (uid,cid,external,title,note,url,due,uncertain));count+=1
            cur.execute('UPDATE classroom_connections SET last_sync=NOW(),last_error=NULL WHERE user_id=%s',(uid,));conn.commit()
        return jsonify(ok=True,imported=count)

    @app.get('/api/classroom/assignments')
    @private
    def assignments(uid):
        with db() as (_,cur):
            cur.execute('''SELECT a.* FROM classroom_assignments a JOIN classroom_connections c ON c.user_id=a.user_id
                WHERE a.user_id=%s AND c.selected_courses ? a.course_id ORDER BY a.available DESC,a.due_at NULLS LAST,a.id LIMIT 1500''',(uid,));rows=cur.fetchall()
        return jsonify(assignments=rows)

    @app.post('/api/classroom/assignments/<int:aid>/planner')
    @private
    def planner(uid,aid):
        confirmed()
        with db() as (conn,cur):
            cur.execute('SELECT user_id FROM classroom_connections WHERE user_id=%s FOR UPDATE',(uid,))
            if not cur.fetchone():raise ValueError('Connect Classroom first.')
            cur.execute('''SELECT a.* FROM classroom_assignments a JOIN classroom_connections c ON c.user_id=a.user_id
                WHERE a.id=%s AND a.user_id=%s AND c.selected_courses ? a.course_id FOR UPDATE OF a''',(aid,uid));a=cur.fetchone()
            if not a:return jsonify(error='Assignment not found.'),404
            if a['task_id']:return jsonify(task_id=a['task_id'],replayed=True)
            if not a['available']:raise ValueError('This assignment is no longer available. Check Classroom.')
            cur.execute('''INSERT INTO tasks(user_id,title,details,due_at,priority,completed,created_at,updated_at)
                VALUES(%s,%s,%s,%s,'medium',FALSE,NOW(),NOW()) RETURNING id''',
                (uid,a['title'][:180],('Classroom assignment; completion here is not official submission.\n'+a['original_url']+'\n'+a['instructions'])[:1000],a['due_at']))
            tid=cur.fetchone()['id'];cur.execute('UPDATE classroom_assignments SET task_id=%s WHERE id=%s',(tid,aid));conn.commit()
        return jsonify(task_id=tid),201

    @app.post('/api/classroom/disconnect')
    @private
    def disconnect(uid):
        data=confirmed()
        if type(data.get('remove_imports')) is not bool:raise ValueError('Choose whether to remove imported assignments. Planner tasks are retained.')
        encrypted=None
        with db() as (conn,cur):
            cur.execute('DELETE FROM classroom_connections WHERE user_id=%s RETURNING refresh_cipher',(uid,));row=cur.fetchone()
            encrypted=row['refresh_cipher'] if row else None
            cur.execute('DELETE FROM classroom_oauth_requests WHERE user_id=%s',(uid,))
            if data['remove_imports']:cur.execute('DELETE FROM classroom_assignments WHERE user_id=%s',(uid,))
            conn.commit()
        revoked=not encrypted
        if encrypted:
            try:
                token=cipher().decrypt(encrypted.encode()).decode()
                response=requests.post('https://oauth2.googleapis.com/revoke',data={'token':token},timeout=(5,10),allow_redirects=False)
                revoked=response.status_code==200
            except (ProviderError,InvalidToken,requests.RequestException):pass
        return jsonify(ok=True,revoked=revoked,planner_tasks_retained=True)
