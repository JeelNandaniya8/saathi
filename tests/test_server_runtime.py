import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
import requests
from server_runtime import serve
import server_runtime


def test_worker_database_preparation_releases_lease_and_never_exposes_failures(monkeypatch, capsys):
    import db_pool
    from unittest.mock import Mock
    connect = Mock()
    monkeypatch.setattr(db_pool, 'connect', connect)
    server_runtime.prepare_worker_database('')
    connect.assert_not_called()
    server_runtime.prepare_worker_database('fixture-dsn')
    connect.return_value.close.assert_called_once()
    assert 'Database worker connection: ready' in capsys.readouterr().out
    for failure in ('connect', 'release'):
        connect.reset_mock()
        connect.side_effect = RuntimeError('PRIVATE_DATABASE_DETAILS') if failure == 'connect' else None
        connect.return_value.close.side_effect = RuntimeError('PRIVATE_DATABASE_DETAILS') if failure == 'release' else None
        with pytest.raises(RuntimeError, match='Database worker could not initialize') as error:
            server_runtime.prepare_worker_database('fixture-dsn')
        assert error.value.__suppress_context__
        assert 'PRIVATE_DATABASE_DETAILS' not in str(error.value)
        assert 'ready' not in capsys.readouterr().out


@pytest.mark.parametrize('entrypoint', ['legacy', 'wsgi'])
def test_real_render_worker_prepares_database_before_first_health_request(entrypoint):
    pytest.importorskip('gunicorn')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    fixture = '''import os,sys,types,time
from flask import Flask
from server_runtime import serve
parent=os.getpid()
state={'calls':0,'released':False,'pid':None}
def connect(dsn):
 assert dsn=='fixture-dsn'
 assert os.getpid()!=parent, 'Never open the worker connection before fork'
 state['calls']+=1;state['pid']=os.getpid()
 time.sleep(.25)
 class Lease:
  def close(self):state['released']=True
 return Lease()
sys.modules['db_pool']=types.SimpleNamespace(connect=connect)
app=Flask(__name__)
@app.get('/health')
def health():return {'calls':state['calls'],'released':state['released'],'worker_pid':state['pid']==os.getpid()}
if os.environ['FIXTURE_ENTRYPOINT']=='legacy':
 serve(app)
else:
 sys.modules['fixture_app']=types.SimpleNamespace(app=app)
 sys.argv=['gunicorn','--bind','127.0.0.1:'+os.environ['PORT'],'--workers','1','--threads','8','fixture_app:app']
 from gunicorn.app.wsgiapp import run
 run()
'''
    env = {**os.environ, 'RENDER':'true', 'PORT':str(port), 'DATABASE_URL':'fixture-dsn',
           'FLASK_SECRET_KEY':'fixture-stable-signing-key-not-production', 'GUNICORN_CMD_ARGS':'',
           'FIXTURE_ENTRYPOINT':entrypoint}
    process = subprocess.Popen([sys.executable, '-c', fixture], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 12
        while True:
            try:
                result = requests.get(f'http://127.0.0.1:{port}/health', timeout=.5)
                if result.status_code == 200: break
            except requests.RequestException: pass
            if process.poll() is not None or time.monotonic() > deadline:
                raise AssertionError('Worker fixture did not become ready')
            time.sleep(.05)
        assert result.json() == {'calls':1, 'released':True, 'worker_pid':True}
        for _ in range(2):
            assert requests.get(f'http://127.0.0.1:{port}/health', timeout=1).json() == result.json()
    finally:
        process.terminate()
        try: output, logs = process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill(); output, logs = process.communicate(timeout=3)
    assert output.count('Database worker connection: ready') == 1
    assert 'fixture-dsn' not in output + logs


def test_local_development_and_invalid_port():
    class App:
        def run(self,**kwargs):self.options=kwargs
    app=App();serve(app,{'PORT':'8765','FLASK_DEBUG':'true'})
    assert app.options=={'host':'0.0.0.0','port':8765,'debug':True}
    with pytest.raises(ValueError):serve(app,{'PORT':'0'})
    for key in ('','short'):
        with pytest.raises(RuntimeError,match='persistent FLASK_SECRET_KEY'):
            serve(app,{'PORT':'8765','RENDER':'true','FLASK_SECRET_KEY':key})


def test_real_render_entry_runs_gunicorn_and_health_during_stream():
    pytest.importorskip('gunicorn')
    with socket.socket() as socket_probe:
        socket_probe.bind(('127.0.0.1',0));port=socket_probe.getsockname()[1]
    fixture='''from flask import Flask,Response
import time
from server_runtime import serve
app=Flask(__name__);app.debug=True
@app.get('/health')
def health():return {'debug':app.debug,'ready':True}
@app.get('/stream')
def stream():
 def chunks():
  yield b'first\\n'
  time.sleep(3)
  yield b'last\\n'
 return Response(chunks(),mimetype='text/plain')
serve(app)
'''
    environment={**os.environ,'RENDER':'true','PORT':str(port),'FLASK_DEBUG':'true','DATABASE_URL':'',
                 'FLASK_SECRET_KEY':'fixture-stable-signing-key-not-production',
                 'GUNICORN_CMD_ARGS':'--workers 99 --access-logfile -'}
    process=subprocess.Popen([sys.executable,'-c',fixture],env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    base=f'http://127.0.0.1:{port}'
    try:
        deadline=time.monotonic()+12
        while True:
            try:
                ready=requests.get(base+'/health',timeout=.5)
                if ready.status_code==200:break
            except requests.RequestException:pass
            if process.poll() is not None or time.monotonic()>deadline:raise AssertionError('Gunicorn fixture did not start')
            time.sleep(.05)
        assert ready.json()=={'debug':False,'ready':True}
        with requests.get(base+'/stream',stream=True,timeout=5) as stream:
            chunks=stream.iter_lines(chunk_size=1);assert next(chunks)==b'first'
            # A blocking single worker cannot serve this before the stream finishes.
            with ThreadPoolExecutor(max_workers=1) as executor:
                health=executor.submit(requests.get,base+'/health',timeout=1.5)
                assert health.result(timeout=2).json()['ready']
            assert next(chunks)==b'last'
    finally:
        process.terminate()
        try:output,logs=process.communicate(timeout=8)
        except subprocess.TimeoutExpired:process.kill();output,logs=process.communicate(timeout=3)
    assert 'Session signing configuration:' in output
    assert 'Using worker: gthread' in logs and 'development server' not in logs
