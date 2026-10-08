"""User-entered food planning and explicitly accepted, limited care sharing.

No AI, inferred treatment, automatic escalation or messages are sent here.
"""
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from uuid import UUID
from flask import jsonify, request
from psycopg2.extras import Json
import care_routines


def food_preview(data):
    if not isinstance(data, dict) or data.get('confirmed') is not True:
        raise ValueError('Confirm these user-entered food preferences first.')
    options = data.get('options')
    if not isinstance(options, list) or not 1 <= len(options) <= 20:
        raise ValueError('Enter 1–20 food options and their ingredients.')
    if type(data.get('days')) is not int or not 1 <= data['days'] <= 7:
        raise ValueError('Choose 1–7 days.')
    for key in ('clinical_context', 'clinician_reviewed_options'):
        if type(data.get(key)) is not bool:
            raise ValueError('Choose whether clinical review is needed and whether options were reviewed.')
    allergens = data.get('allergens', [])
    restrictions = data.get('restrictions', '')
    preference = data.get('preferences', '')
    currency = data.get('currency', 'INR')
    if not isinstance(allergens,list) or len(allergens)>20 or any(not isinstance(x,str) or not 1<=len(x.strip())<=60 for x in allergens):
        raise ValueError('Enter up to 20 explicit allergens or avoidances.')
    if any(not isinstance(x,str) or len(x)>500 for x in (restrictions,preference)):
        raise ValueError('Keep preferences and clinician restrictions within 500 characters each.')
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isascii() or not currency.isalpha():
        raise ValueError('Use a three-letter currency code.')
    def amount(value):
        if value in (None,''):return None
        if isinstance(value,bool) or len(str(value))>40:raise ValueError('Enter a valid user-estimated cost.')
        try:
            number=Decimal(str(value))
            if not number.is_finite() or not 0<=number<=100000:raise ValueError()
            return number.quantize(Decimal('.01'))
        except (InvalidOperation,ValueError):raise ValueError('Enter a valid user-estimated cost.') from None
    budget=amount(data.get('daily_budget'))
    normalized=[]
    for option in options:
        if not isinstance(option,dict) or not isinstance(option.get('name'),str) or not 1<=len(option['name'].strip())<=160:
            raise ValueError('Enter a short name for every food option.')
        ingredients=option.get('ingredients')
        if not isinstance(ingredients,list) or not 1<=len(ingredients)<=30 or any(not isinstance(i,str) or not 1<=len(i.strip())<=80 for i in ingredients):
            raise ValueError('List all known ingredients for each option; do not guess.')
        cost=amount(option.get('cost'))
        normalized.append({'name':option['name'].strip(),'ingredients':[i.strip() for i in ingredients], 'cost':str(cost) if cost is not None else None})
    needs_review=bool(data['clinical_context'] or allergens or restrictions.strip())
    reviewed=data['clinician_reviewed_options']
    blocked=[];eligible=[]
    for option in normalized:
        # Conservative text matching is only an extra check, never allergy clearance.
        haystack=' '.join([option['name'],*option['ingredients']]).casefold()
        if any(a.strip().casefold() in haystack for a in allergens):blocked.append(option['name'])
        else:eligible.append(option)
    items=[];unscheduled=data['days']*3
    if not needs_review or reviewed:
        for day in range(1,data['days']+1):
            remaining=budget
            for slot in range(3):
                choices=[o for o in eligible if remaining is None or (o['cost'] is not None and Decimal(o['cost'])<=remaining)]
                if not choices:continue
                option=choices[((day-1)*3+slot)%len(choices)]
                items.append({'day':day,'slot':slot,'name':option['name'],'ingredients':option['ingredients'],'estimated_cost':option['cost']})
                if remaining is not None:remaining-=Decimal(option['cost'])
        unscheduled-=len(items)
    inputs={'options':normalized,'days':data['days'],'allergens':[x.strip() for x in allergens], 'restrictions':restrictions.strip(),'preferences':preference.strip(),
        'clinical_context':data['clinical_context'],'clinician_reviewed_options':reviewed,'daily_budget':str(budget) if budget is not None else None,'currency':currency.upper()}
    result={'items':items,'unscheduled':unscheduled,'blocked_options':blocked,'needs_clinical_review':needs_review and not reviewed,
        'unverified_clinician_source':needs_review and reviewed,'cost_uncertain':any(o['cost'] is None for o in normalized),
        'inputs':inputs,'generated_by_ai':False,'estimated_only':True,
        'warning':'User-entered food choices and estimated costs only, not a therapeutic diet or allergy clearance. Check actual ingredients, labels and cross-contact. No quantities, calories, carbs, fluid prescription or medicine changes are inferred.'}
    result['preview_token']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


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
        return wrapped
    def confirmed():
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or data.get('confirmed') is not True:raise ValueError('Confirm this action first.')
        return data

    @app.post('/api/care/food-plans/preview')
    @private
    def preview(uid):return jsonify(plan=food_preview(request.get_json(silent=True)))

    @app.route('/api/care/food-plans',methods=['GET','POST'])
    @private
    def food_plans(uid):
        if request.method=='GET':
            with db() as (_,cur):
                cur.execute('SELECT id,preview,created_at FROM food_plans WHERE user_id=%s ORDER BY id DESC LIMIT 30',(uid,));rows=cur.fetchall()
            return jsonify(plans=rows)
        data=confirmed()
        if data.get('save_confirmed') is not True:raise ValueError('Confirm storing this plan, including any user-entered health restrictions.')
        try:client_id=str(UUID(str(data.get('client_id'))))
        except ValueError:raise ValueError('Reopen the form before saving.') from None
        plan=food_preview(data)
        if data.get('preview_token')!=plan['preview_token']:return jsonify(error='Choices changed. Preview again.'),409
        if not plan['items']:raise ValueError('Review food choices with a qualified professional before saving a plan.')
        with db() as (conn,cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
            cur.execute('SELECT id FROM food_plans WHERE user_id=%s AND client_id=%s',(uid,client_id));saved=cur.fetchone()
            if saved:return jsonify(id=saved['id'],replayed=True)
            cur.execute('SELECT COUNT(*) n FROM food_plans WHERE user_id=%s',(uid,))
            if cur.fetchone()['n']>=30:raise ValueError('Keep up to 30 food plans. Remove an older one first.')
            cur.execute('INSERT INTO food_plans(user_id,client_id,inputs,preview) VALUES(%s,%s,%s,%s) RETURNING id',(uid,client_id,Json(plan['inputs']),Json(plan)))
            saved=cur.fetchone();conn.commit()
        return jsonify(id=saved['id']),201

    @app.delete('/api/care/food-plans/<int:pid>')
    @private
    def delete_food(uid,pid):
        confirmed()
        with db() as (conn,cur):
            cur.execute('DELETE FROM food_plans WHERE id=%s AND user_id=%s RETURNING id',(pid,uid))
            if not cur.fetchone():return jsonify(error='Plan not found.'),404
            conn.commit()
        return jsonify(ok=True)

    def relationship(cur,owner,recipient):
        cur.execute("SELECT id FROM trusted_contacts WHERE status='accepted' AND ((owner_user_id=%s AND contact_user_id=%s) OR (owner_user_id=%s AND contact_user_id=%s)) LIMIT 1",(owner,recipient,recipient,owner))
        return bool(cur.fetchone())

    @app.route('/api/care/shares',methods=['GET','POST'])
    @private
    def shares(uid):
        if request.method=='GET':
            with db() as (_,cur):
                cur.execute('SELECT s.id,s.owner_id,s.recipient_id,s.fields,s.status,s.expires_at,s.version,jsonb_array_length(s.routine_ids) routine_count,u.name owner_name,r.name recipient_name FROM care_shares s JOIN users u ON u.id=s.owner_id JOIN users r ON r.id=s.recipient_id WHERE s.owner_id=%s OR s.recipient_id=%s ORDER BY s.id DESC LIMIT 100',(uid,uid));rows=cur.fetchall()
                cur.execute("SELECT DISTINCT u.id,u.name FROM trusted_contacts t JOIN users u ON u.id=CASE WHEN t.owner_user_id=%s THEN t.contact_user_id ELSE t.owner_user_id END WHERE t.status='accepted' AND (t.owner_user_id=%s OR t.contact_user_id=%s)",(uid,uid,uid));contacts=cur.fetchall()
            return jsonify(shares=rows,contacts=contacts,enabled=care_routines.enabled(),user_id=uid)
        if not care_routines.enabled():return jsonify(error='Care sharing needs the clinical beta gate.'),503
        data=confirmed();recipient=data.get('recipient_id');routines=data.get('routine_ids');fields=data.get('fields');days=data.get('days')
        if type(recipient) is not int or recipient==uid or type(days) is not int or not 1<=days<=30:raise ValueError('Choose a different accepted contact and 1–30 days.')
        if not isinstance(routines,list) or not 1<=len(routines)<=10 or any(type(i) is not int for i in routines) or len(set(routines))!=len(routines):raise ValueError('Choose 1–10 owned medication schedules.')
        if not isinstance(fields,list) or 'status' not in fields or any(not isinstance(f,str) or f not in ('status','title','instructions') for f in fields) or len(set(fields))!=len(fields):raise ValueError('Choose the exact fields to share; status is required.')
        with db() as (conn,cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
            if not relationship(cur,uid,recipient):raise ValueError('Both people must first accept a trusted-contact connection.')
            cur.execute("SELECT id FROM reminders WHERE user_id=%s AND kind='medication' AND id=ANY(%s)",(uid,routines))
            if len(cur.fetchall())!=len(routines):return jsonify(error='Schedule not found.'),404
            cur.execute("""INSERT INTO care_shares(owner_id,recipient_id,routine_ids,fields,expires_at) VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(owner_id,recipient_id) DO UPDATE SET routine_ids=EXCLUDED.routine_ids,fields=EXCLUDED.fields,expires_at=EXCLUDED.expires_at,status='pending',version=care_shares.version+1 RETURNING id""",
                (uid,recipient,Json(routines),Json(fields),datetime.now(timezone.utc)+timedelta(days=days)))
            row=cur.fetchone();conn.commit()
        return jsonify(id=row['id'],status='pending'),201

    @app.post('/api/care/shares/<int:sid>/respond')
    @private
    def respond(uid,sid):
        data=confirmed();action=data.get('action')
        if action not in ('accept','revoke'):raise ValueError('Choose accept or revoke.')
        with db() as (conn,cur):
            cur.execute('SELECT * FROM care_shares WHERE id=%s AND (owner_id=%s OR recipient_id=%s) FOR UPDATE',(sid,uid,uid));row=cur.fetchone()
            if not row:return jsonify(error='Request not found.'),404
            if type(data.get('version')) is not int or data['version']!=row['version']:return jsonify(error='Request changed. Review again.'),409
            if action=='accept':
                if not care_routines.enabled():return jsonify(error='Care sharing is not enabled.'),503
                if row['recipient_id']!=uid or row['status']!='pending' or row['expires_at']<=datetime.now(timezone.utc) or not relationship(cur,row['owner_id'],uid):raise ValueError('This request cannot be accepted.')
            cur.execute('UPDATE care_shares SET status=%s,version=version+1 WHERE id=%s',('accepted' if action=='accept' else 'revoked',sid));conn.commit()
        return jsonify(ok=True)

    @app.get('/api/care/shares/<int:sid>/records')
    @private
    def records(uid,sid):
        if not care_routines.enabled():return jsonify(error='Care sharing is not enabled.'),503
        with db() as (_,cur):
            cur.execute("SELECT * FROM care_shares WHERE id=%s AND recipient_id=%s AND status='accepted' AND expires_at>NOW()",(sid,uid));share=cur.fetchone()
            if not share or not relationship(cur,share['owner_id'],uid):return jsonify(error='Accepted access not found.'),404
            cur.execute("""SELECT r.id,r.title,r.note,r.current_scheduled_for,o.status FROM reminders r
                LEFT JOIN care_occurrences o ON o.reminder_id=r.id AND o.scheduled_for=r.current_scheduled_for
                WHERE r.user_id=%s AND r.kind='medication' AND r.id=ANY(%s) ORDER BY r.id""",(share['owner_id'],share['routine_ids']))
            rows=[]
            for row in cur.fetchall():
                record={'id':row['id'],'scheduled_for':row['current_scheduled_for'],'status':row['status'] or 'not_confirmed'}
                if 'title' in share['fields']:record['title']=row['title']
                if 'instructions' in share['fields']:record['instructions']=row['note']
                rows.append(record)
        return jsonify(records=rows,read_only=True,emergency_monitoring=False)
