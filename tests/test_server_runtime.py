import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
import requests
from server_runtime import serve


def test_local_development_and_invalid_port():
    class App:
        def run(self,**kwargs):self.options=kwargs
    app=App();serve(app,{'PORT':'8765','FLASK_DEBUG':'true'})
    assert app.options=={'host':'0.0.0.0','port':8765,'debug':True}
    with pytest.raises(ValueError):serve(app,{'PORT':'0'})


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
    environment={**os.environ,'RENDER':'true','PORT':str(port),'FLASK_DEBUG':'true',
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
        try:_,logs=process.communicate(timeout=8)
        except subprocess.TimeoutExpired:process.kill();_,logs=process.communicate(timeout=3)
    assert 'Using worker: gthread' in logs and 'development server' not in logs
