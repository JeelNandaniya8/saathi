"""User-owned, bounded response timings and a factual weekly activity summary."""
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from functools import wraps
from uuid import UUID
from zoneinfo import ZoneInfo
from flask import jsonify, request

ERROR_CODES = {'', 'AI_ACCESS', 'AI_QUOTA', 'AI_MODEL', 'AI_CONFIGURATION', 'AI_BUSY', 'AI_REQUEST', 'AI_TIMEOUT', 'AI_CONNECTION', 'AI_FORMAT', 'CLIENT_ERROR'}


def timing_input(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid timing record.')
    try:
        request_id = str(UUID(str(data.get('request_id', ''))))
    except ValueError:
        raise ValueError('Invalid request reference.') from None
    total, first, conversation = data.get('total_ms'), data.get('first_text_ms'), data.get('conversation_id')
    if type(total) is not int or not 0 <= total <= 300000 or type(conversation) is not int or conversation < 1:
        raise ValueError('Invalid timing record.')
    if first is not None and (type(first) is not int or not 0 <= first <= total):
        raise ValueError('Invalid first-text timing.')
    if data.get('outcome') not in ('complete', 'error', 'cancelled') or not isinstance(data.get('error_code', ''), str) or data.get('error_code', '') not in ERROR_CODES:
        raise ValueError('Invalid timing outcome.')
    return request_id, conversation, first, total, data['outcome'], data.get('error_code', '')


def week_window(now, zone):
    today = now.astimezone(ZoneInfo(zone)).date()
    start = today - timedelta(days=6)
    return start, today, datetime.combine(start, time.min, ZoneInfo(zone)).astimezone(timezone.utc)


def register(app, b):
    @contextmanager
    def db():
        conn = b['get_db'](); cur = conn.cursor()
        try:
            yield conn, cur
        except Exception:
            conn.rollback(); raise
        finally:
            cur.close(); conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            uid = b['require_user_id']()
            if not uid:
                return jsonify(error='Please log in first.'), 401
            try:
                return fn(uid, *args, **kwargs)
            except ValueError as error:
                return jsonify(error=str(error)), 400
        return wrapped

    @app.route('/api/response-timings', methods=['GET', 'POST', 'DELETE'])
    @private
    def response_timings(uid):
        with db() as (conn, cur):
            if request.method == 'POST':
                values = timing_input(request.get_json(silent=True))
                cur.execute('SELECT id FROM conversations WHERE id=%s AND user_id=%s', (values[1], uid))
                if not cur.fetchone():
                    return jsonify(error='Conversation not found.'), 404
                cur.execute('''INSERT INTO response_timings(user_id,request_id,conversation_id,first_text_ms,total_ms,outcome,error_code)
                    VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,request_id) DO NOTHING''', (uid, *values))
                cur.execute('''DELETE FROM response_timings WHERE user_id=%s AND (created_at<NOW()-INTERVAL '30 days'
                    OR id NOT IN (SELECT id FROM response_timings WHERE user_id=%s ORDER BY id DESC LIMIT 100))''', (uid, uid))
                conn.commit()
                return jsonify(ok=True)
            if request.method == 'DELETE':
                cur.execute('DELETE FROM response_timings WHERE user_id=%s', (uid,)); conn.commit()
                return jsonify(ok=True)
            cur.execute("DELETE FROM response_timings WHERE user_id=%s AND created_at<NOW()-INTERVAL '30 days'", (uid,))
            conn.commit()
            cur.execute('''SELECT COUNT(*) AS attempts,COUNT(*) FILTER(WHERE outcome='complete') AS completed,
                COUNT(*) FILTER(WHERE outcome='error') AS errors,COUNT(*) FILTER(WHERE outcome='cancelled') AS cancelled,
                percentile_cont(0.5) WITHIN GROUP(ORDER BY first_text_ms) FILTER(WHERE outcome='complete') AS first_text_ms,
                percentile_cont(0.5) WITHIN GROUP(ORDER BY total_ms) FILTER(WHERE outcome='complete') AS total_ms,
                percentile_cont(0.95) WITHIN GROUP(ORDER BY first_text_ms) FILTER(WHERE outcome='complete') AS p95_first_text_ms
                FROM response_timings WHERE user_id=%s AND created_at>=NOW()-INTERVAL '30 days' ''', (uid,))
            summary = dict(cur.fetchone())
            cur.execute('''SELECT first_text_ms,total_ms,outcome,error_code,created_at FROM response_timings
                WHERE user_id=%s AND created_at>=NOW()-INTERVAL '30 days' ORDER BY id DESC LIMIT 8''', (uid,))
            recent = [{**dict(row), 'created_at': row['created_at'].isoformat()} for row in cur.fetchall()]
        return jsonify(summary=summary, recent=recent, source='browser', window_days=30)

    @app.get('/api/weekly-review')
    @private
    def weekly_review(uid):
        now = datetime.now(timezone.utc)
        with db() as (_, cur):
            cur.execute('SELECT timezone FROM workspace_preferences WHERE user_id=%s', (uid,))
            pref = cur.fetchone(); zone = pref['timezone'] if pref else 'UTC'
            start, today, since = week_window(now, zone)
            cur.execute('''SELECT
                (SELECT COUNT(*) FROM tasks WHERE user_id=%s AND completed=TRUE AND completed_at>=%s AND completed_at<=%s) AS completed_tasks,
                (SELECT COUNT(*) FROM habit_entries WHERE user_id=%s AND entry_date BETWEEN %s AND %s) AS habit_completions,
                (SELECT COUNT(*) FROM tasks WHERE user_id=%s AND completed=FALSE) AS open_tasks,
                (SELECT COUNT(*) FROM mock_test_attempts WHERE user_id=%s AND created_at BETWEEN %s AND %s) AS practice_attempts,
                (SELECT ROUND(100.0*SUM(score)/NULLIF(SUM(total_questions),0),1) FROM mock_test_attempts
                    WHERE user_id=%s AND created_at BETWEEN %s AND %s) AS practice_accuracy''',
                (uid, since, now, uid, start, today, uid, uid, since, now, uid, since, now))
            summary = dict(cur.fetchone())
            if summary['practice_accuracy'] is not None:
                summary['practice_accuracy'] = float(summary['practice_accuracy'])
        return jsonify(start=start.isoformat(), end=today.isoformat(), timezone=zone, summary=summary,
            note='Task completion dates are tracked from this update. Earlier completed tasks are not assigned guessed dates.')
