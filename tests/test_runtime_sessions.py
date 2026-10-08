"""A configured signing key must validate an existing cookie after process restart."""
import os
import subprocess
import sys

def test_cookie_survives_two_real_backend_processes_with_configured_key():
    env={**os.environ,'DATABASE_URL':'','FLASK_SECRET_KEY':'restart-test-key-only-not-production'}
    first="import app; print(app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':7,'session_version':3}))"
    cookie=subprocess.check_output([sys.executable,'-c',first],env=env,text=True).strip()
    second="import sys,app; print(app.app.session_interface.get_signing_serializer(app.app).loads(sys.stdin.read())['user_id'])"
    result=subprocess.run([sys.executable,'-c',second],input=cookie,env=env,text=True,capture_output=True,check=True)
    assert result.stdout.strip()=='7'
