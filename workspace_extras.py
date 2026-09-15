"""Private quick notes and validated Google profile pictures."""
from contextlib import contextmanager
from functools import wraps
from urllib.parse import urlsplit
from uuid import UUID

from flask import jsonify, request


def avatar_url(value):
    if not isinstance(value,str) or not value or len(value)>2048 or any(c.isspace() or c=='\\' for c in value):
        return None
    try:
        url=urlsplit(value)
        if url.scheme!='https' or url.username or url.password or url.port not in (None,443):return None
        host=(url.hostname or '').lower()
        if not host.endswith('.googleusercontent.com') or host.startswith('.'):return None
        return value
    except ValueError:
        return None


def note_fields(data):
    if not isinstance(data,dict):raise ValueError('Use a valid note.')
    content=data.get('content')
    title=data.get('title','')
    if not isinstance(content,str) or not 1<=len(content.strip())<=10000 or len(content)>10000:
        raise ValueError('Write a note of 1–10,000 characters.')
    if not isinstance(title,str) or len(title)>80:raise ValueError('Use a title of up to 80 characters.')
    return title.strip() or content.strip().splitlines()[0][:80],content.strip()


def note_dict(row):
    return {key:(row[key].isoformat() if key.endswith('_at') else str(row[key]) if key=='client_id' else row[key])
            for key in ('id','client_id','title','content','version','created_at','updated_at')}


def register(app,b):
    @contextmanager
    def db():
        conn=b['get_db']();cur=conn.cursor()
        try:yield conn,cur
        except Exception:
            conn.rollback();raise
        finally:cur.close();conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            uid=b['require_user_id']()
            if not uid:return jsonify(error='Please log in first.'),401
            try:return fn(uid,*args,**kwargs)
            except ValueError as error:return jsonify(error=str(error)),400
        return wrapped

    @app.get('/api/quick-notes')
    @private
    def list_notes(uid):
        with db() as (_,cur):
            cur.execute('SELECT * FROM quick_notes WHERE user_id=%s ORDER BY updated_at DESC,id DESC LIMIT 100',(uid,))
            notes=cur.fetchall()
        return jsonify(notes=[note_dict(row) for row in notes],limit=100)

    @app.post('/api/quick-notes')
    @private
    def create_note(uid):
        data=request.get_json(silent=True);title,content=note_fields(data)
        try:client_id=str(UUID(str(data.get('client_id',''))))
        except (ValueError,TypeError):raise ValueError('Refresh the note editor and try again.') from None
        limited=b['limited']('quick_note',str(uid),30,5)
        if limited:return limited
        with db() as (conn,cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,));cur.fetchone()
            cur.execute('SELECT * FROM quick_notes WHERE user_id=%s AND client_id=%s',(uid,client_id));existing=cur.fetchone()
            if existing:return jsonify(note=note_dict(existing),replayed=True)
            cur.execute('SELECT COUNT(*) AS count FROM quick_notes WHERE user_id=%s',(uid,))
            if cur.fetchone()['count']>=100:raise ValueError('You have 100 notes. Remove one before adding another.')
            cur.execute('INSERT INTO quick_notes(user_id,client_id,title,content) VALUES(%s,%s,%s,%s) RETURNING *',(uid,client_id,title,content))
            note=cur.fetchone();conn.commit()
        return jsonify(note=note_dict(note)),201

    @app.route('/api/quick-notes/<int:note_id>',methods=['PATCH','DELETE'])
    @private
    def change_note(uid,note_id):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']<1:
            raise ValueError('Refresh this note before changing it.')
        with db() as (conn,cur):
            cur.execute('SELECT * FROM quick_notes WHERE id=%s AND user_id=%s FOR UPDATE',(note_id,uid));note=cur.fetchone()
            if not note:return jsonify(error='Note not found.'),404
            if note['version']!=data['version']:
                return jsonify(error='This note changed on another device. Your draft is still here. Reload the saved note before editing it.',note=note_dict(note)),409
            if request.method=='DELETE':
                cur.execute('DELETE FROM quick_notes WHERE id=%s AND user_id=%s',(note_id,uid));conn.commit()
                return jsonify(ok=True)
            title,content=note_fields(data)
            cur.execute('UPDATE quick_notes SET title=%s,content=%s,version=version+1,updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING *',(title,content,note_id,uid))
            updated=cur.fetchone();conn.commit()
        return jsonify(note=note_dict(updated))
