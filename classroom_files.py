"""Explicit per-file Google Picker grant, then the existing Chat upload path.

No refresh tokens, background downloads, AI calls, local files, or broader
Classroom scopes. Disabled until the owner enables the Google Picker API.
"""
import base64
import hashlib
import io
import json
import os
import re
import secrets
import time
import uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,quote

import requests
from cryptography.fernet import InvalidToken
from flask import jsonify,request,session,redirect,send_file

DRIVE_SCOPE='https://www.googleapis.com/auth/drive.file'
DRIVE='https://www.googleapis.com/drive/v3/files/'
MAX_BYTES=5*1024*1024
NATIVE={'application/vnd.google-apps.document','application/vnd.google-apps.presentation','application/vnd.google-apps.spreadsheet'}
ALLOWED={'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}

def enabled():
    return os.environ.get('CLASSROOM_FILE_PICKER_ENABLED','').lower()=='true'

def source_hash(source):
    fields={k:source[k] for k in ('id','course_id','external_id','file_materials')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def bounded_download(token,file_id,mime):
    """Read only a selected fixed-host resource, without bearer redirects."""
    if not isinstance(file_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',file_id):
        raise ValueError('file_unavailable')
    if not isinstance(mime,str) or (mime not in ALLOWED and mime not in NATIVE):raise ValueError('file_type')
    url=DRIVE+file_id
    params={'alt':'media'}
    if mime in NATIVE:url+='/export';params={'mimeType':'application/pdf'}
    response=None;deadline=time.monotonic()+20
    try:
        response=requests.get(url,params=params,headers={'Authorization':'Bearer '+token},
            stream=True,timeout=(5,6),allow_redirects=False)
        if response.status_code!=200:raise ValueError('file_permission' if response.status_code in (401,403) else 'file_provider')
        length=response.headers.get('Content-Length')
        if length and (not length.isdigit() or int(length)>MAX_BYTES):raise ValueError('file_size')
        data=bytearray()
        for chunk in response.iter_content(64*1024):
            if time.monotonic()>deadline:raise ValueError('file_provider')
            data.extend(chunk)
            if len(data)>MAX_BYTES:raise ValueError('file_size')
        if not data:raise ValueError('file_empty')
        output='application/pdf' if mime in NATIVE else mime
        signatures={'application/pdf':data[:5]==b'%PDF-','image/png':data[:8]==b'\x89PNG\r\n\x1a\n',
            'image/jpeg':data[:3]==b'\xff\xd8\xff','image/webp':data[:4]==b'RIFF' and data[8:12]==b'WEBP'}
        if not signatures[output]:raise ValueError('file_type')
        return bytes(data),output
    except requests.RequestException:raise ValueError('file_provider') from None
    finally:
        if response is not None:response.close()

def register(app,b,cc,db,private,confirmed):
    def selected(cur,uid,aid,fid):
        cur.execute("""SELECT a.id,a.course_id,a.external_id,a.file_materials,c.version
            FROM classroom_assignments a JOIN classroom_connections c ON c.user_id=a.user_id
            WHERE a.id=%s AND a.user_id=%s AND a.available AND c.selected_courses ? a.course_id""",(aid,uid))
        row=cur.fetchone()
        if not row or not isinstance(row['file_materials'],list):raise ValueError('file_unavailable')
        file=next((f for f in row['file_materials'] if f.get('id')==fid),None)
        if not file:raise ValueError('file_unavailable')
        return row,file

    def current(cur,uid,gid,lock=False):
        cur.execute('SELECT * FROM classroom_file_grants WHERE id=%s AND user_id=%s'+(' FOR UPDATE' if lock else ''),(gid,uid))
        grant=cur.fetchone()
        if not grant or grant['expires_at']<=datetime.now(timezone.utc) or grant['session_version']!=session.get('session_version'):
            raise ValueError('file_expired')
        source,file=selected(cur,uid,grant['assignment_id'],grant['drive_id'])
        if source['version']!=grant['connection_version'] or source_hash(source)!=grant['source_hash']:
            raise ValueError('file_changed')
        return grant,file

    @app.post('/api/classroom/assignments/<int:aid>/files/<fid>/authorize')
    @private
    def authorize_file(uid,aid,fid):
        data=confirmed()
        if data.get('file_confirmed') is not True:raise ValueError('file_consent')
        config=cc.configuration()
        if not enabled() or not config:raise ValueError('file_not_configured')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',fid):raise ValueError('file_unavailable')
        state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with db() as (conn,cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
            source,_=selected(cur,uid,aid,fid)
            payload=dict(purpose='assignment_file',verifier=verifier,assignment_id=aid,drive_id=fid,
                source_hash=source_hash(source),version=source['version'])
            cur.execute('DELETE FROM classroom_file_grants WHERE user_id=%s AND expires_at<=NOW()',(uid,))
            cur.execute("""INSERT INTO classroom_oauth_requests(user_id,state_hash,verifier_cipher,session_version,expires_at)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET state_hash=EXCLUDED.state_hash,
                verifier_cipher=EXCLUDED.verifier_cipher,session_version=EXCLUDED.session_version,expires_at=EXCLUDED.expires_at""",
                (uid,hashlib.sha256(state.encode()).hexdigest(),cc.cipher().encrypt(json.dumps(payload).encode()).decode(),
                session.get('session_version'),datetime.now(timezone.utc)+timedelta(minutes=10)))
            conn.commit()
        return jsonify(url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({
            'client_id':config[0],'redirect_uri':config[2],'response_type':'code','scope':DRIVE_SCOPE,
            'access_type':'online','prompt':'consent','include_granted_scopes':'false',
            'trigger_onepick':'true','file_ids':fid,'allow_multiple':'false',
            'state':state,'code_challenge':challenge,'code_challenge_method':'S256'}))

    def finish_file(uid,pending,payload):
        """Called only after the existing one-use, owner/session-bound state check."""
        if request.args.get('error'):return redirect('/dashboard?classroom_result=file_cancelled#study')
        try:
            if not enabled():raise ValueError('file_not_configured')
            code=request.args.get('code','')
            if not code or len(code)>4096 or request.args.getlist('picked_file_ids')!=[payload['drive_id']]:
                raise ValueError('file_selection')
            config=cc.configuration()
            with db() as (_,cur):
                source,_=selected(cur,uid,payload['assignment_id'],payload['drive_id'])
                if source['version']!=payload['version'] or source_hash(source)!=payload['source_hash']:
                    raise ValueError('file_changed')
            with cc.provider_budget(12):
                tokens=cc.provider_json('POST',cc.TOKEN,data={'client_id':config[0],'client_secret':config[1],
                    'redirect_uri':config[2],'code':code,'code_verifier':payload['verifier'],'grant_type':'authorization_code'})
            if not isinstance(tokens.get('scope'),str) or set(tokens['scope'].split())!={DRIVE_SCOPE}:
                raise ValueError('file_permission')
            token=tokens.get('access_token');ttl=tokens.get('expires_in')
            if not isinstance(token,str) or not token or len(token)>8192 or '\r' in token or '\n' in token or type(ttl) is not int or ttl<30:
                raise ValueError('file_permission')
            grant=str(uuid.uuid4())
            with db() as (conn,cur):
                cur.execute('SELECT session_version FROM users WHERE id=%s FOR UPDATE',(uid,))
                user=cur.fetchone()
                if not user or user['session_version']!=pending['session_version']:raise ValueError('file_expired')
                cur.execute('SELECT user_id FROM classroom_connections WHERE user_id=%s FOR SHARE',(uid,))
                source,_=selected(cur,uid,payload['assignment_id'],payload['drive_id'])
                if source['version']!=payload['version'] or source_hash(source)!=payload['source_hash']:
                    raise ValueError('file_changed')
                cur.execute("""INSERT INTO classroom_file_grants(id,user_id,assignment_id,drive_id,source_hash,
                    connection_version,session_version,access_cipher,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (grant,uid,payload['assignment_id'],payload['drive_id'],payload['source_hash'],payload['version'],
                    pending['session_version'],cc.cipher().encrypt(token.encode()).decode(),
                    datetime.now(timezone.utc)+timedelta(seconds=min(ttl-15,600))))
                conn.commit()
            return redirect('/chat?classroom_file='+grant)
        except (ValueError,KeyError,TypeError):
            return redirect('/dashboard?classroom_result=file_failed#study')
        except cc.ProviderError:
            return redirect('/dashboard?classroom_result=file_failed#study')

    @app.get('/api/classroom/files/<uuid:gid>/download')
    @private
    def download_file(uid,gid):
        if not enabled():return jsonify(error_code='file_not_configured'),503
        limit=b['limited']('classroom_file_download',str(uid),6,10)
        if limit:return limit
        try:
            with db() as (_,cur):grant,file=current(cur,uid,str(gid))
            try:token=cc.cipher().decrypt(grant['access_cipher'].encode()).decode()
            except (InvalidToken,UnicodeError):raise ValueError('file_expired') from None
            with cc.provider_budget(12):
                meta=cc.provider_json('GET',DRIVE+grant['drive_id'],headers={'Authorization':'Bearer '+token},
                    params={'fields':'id,mimeType,size,capabilities(canDownload)'})
            capabilities=meta.get('capabilities',{})
            if not isinstance(capabilities,dict):raise ValueError('file_provider')
            if meta.get('id')!=grant['drive_id'] or capabilities.get('canDownload') is False:
                raise ValueError('file_permission')
            size=meta.get('size')
            if size is not None and (not str(size).isdigit() or int(size)>MAX_BYTES):raise ValueError('file_size')
            content,mime=bounded_download(token,grant['drive_id'],meta.get('mimeType'))
            digest=hashlib.sha256(content).hexdigest()
            with db() as (conn,cur):
                cur.execute('SELECT user_id FROM classroom_connections WHERE user_id=%s FOR SHARE',(uid,))
                latest,_=current(cur,uid,str(gid),True)
                if latest['download_hash'] and latest['download_hash']!=digest:raise ValueError('file_changed')
                cur.execute('UPDATE classroom_file_grants SET download_hash=%s WHERE id=%s',(digest,str(gid)));conn.commit()
            title=re.sub(r'[\x00-\x1f\x7f/\\]','_',file['title']).strip()[:180] or 'Classroom file'
            suffix=ALLOWED[mime]
            if not title.lower().endswith(('.jpg','.jpeg') if mime=='image/jpeg' else (suffix,)):title+=suffix
            response=send_file(io.BytesIO(content),mimetype=mime,as_attachment=True,download_name=title,max_age=0)
            response.headers['Cache-Control']='private, no-store'
            response.headers['X-Content-Type-Options']='nosniff'
            response.headers['X-Saathi-File-Name']=quote(title,safe='')
            response.headers['X-Saathi-File-Modified']=str(int(grant['created_at'].timestamp()*1000))
            return response
        except ValueError as error:
            code=str(error)
            if code not in {'file_expired','file_unavailable','file_changed','file_permission','file_type','file_size','file_empty','file_provider'}:code='file_provider'
            return jsonify(error_code=code),410 if code=='file_expired' else 409 if code=='file_changed' else 400
        except cc.ProviderError as error:
            return jsonify(error_code='file_permission' if error.code in ('reconnect_required','permission_or_admin_block') else 'file_provider'),503

    return finish_file
