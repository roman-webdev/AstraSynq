"""M5 regression on real PostgreSQL and local HTTP/process boundaries."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from app.main import app
from app.database import SessionLocal, engine
from app.models import Event, Job, Delivery, IntegrationConfig, Lead, Import, WorkerHeartbeat, utcnow
from app.config import validate_environment
from app.imports import parse_csv
from app.automation import emit, send, post, resolve_url, PinnedHTTPS
from app.maintenance import cleanup
from app import worker
from auth_helpers import credentials
from test_automation import queue

client = TestClient(app)

def production_env():
    return dict(ASTRASYNQ_MODE='production',AUTH_COOKIE_SECURE='true',AUTH_ALLOWED_ORIGINS='https://app.example.test',DATABASE_URL='postgresql+psycopg://app:synthetic-long-password@db/astrasynq')

@pytest.mark.parametrize('key,value',[
    ('AUTH_COOKIE_SECURE','false'),('AUTH_ALLOWED_ORIGINS',''),('AUTH_ALLOWED_ORIGINS','*'),
    ('AUTH_ALLOWED_ORIGINS','http://app.example.test'),('AUTH_ALLOWED_ORIGINS','https://app.example.test/path'),
    ('AUTH_COOKIE_SAMESITE','none'),('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS','true'),
    ('DATABASE_URL','postgresql://app@db/astrasynq'),('DATABASE_URL','sqlite:///db'),
    ('DATABASE_URL','postgresql://app:passwordpassword@db/astrasynq'),
    ('DATABASE_URL','postgresql://app:synthetic-long-password@remote.example/astrasynq'),
    ('ASTRASYNQ_MODE','prod')])
def test_production_refuses_unsafe_config(key,value):
    env=production_env();env[key]=value
    with pytest.raises(RuntimeError) as exc: validate_environment(env)
    assert 'synthetic-long-password' not in str(exc.value)

def test_production_config_and_remote_tls():
    env=production_env();validate_environment(env)
    env['DATABASE_URL']='postgresql://app:synthetic-long-password@remote.example/astrasynq?sslmode=verify-full'
    validate_environment(env)

def test_production_docs_disabled_and_secure_cookies():
    env={**os.environ,**production_env()}
    script="from app.main import app;from fastapi.testclient import TestClient;c=TestClient(app,base_url='https://app.example.test');r=c.get('/api/v1/auth/csrf');assert 'Secure' in r.headers['set-cookie'] and 'HttpOnly' in r.headers['set-cookie'];assert c.get('/docs').status_code==404;assert c.get('/openapi.json').status_code==404;assert c.get('/health/live').headers['strict-transport-security']=='max-age=31536000';print('production guards pass')"
    result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr

def test_headers_request_id_and_no_http_hsts():
    response=client.get('/health/live',headers={'X-Request-ID':'unsafe injected token'})
    assert response.headers['x-content-type-options']=='nosniff'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert response.headers['x-frame-options']=='DENY'
    UUID(response.headers['x-request-id'])
    assert 'strict-transport-security' not in response.headers

def test_readiness_database_failure(monkeypatch):
    def unavailable(): raise RuntimeError('private database URL')
    monkeypatch.setattr(engine,'connect',unavailable)
    assert client.get('/health/ready').status_code==503
    assert client.get('/health/live').status_code==200

@pytest.mark.parametrize('content,code',[
    (b'email,name\na@x.test\n','csv_columns'),(b'email,name\na@x.test,b,extra\n','csv_columns'),
    (b'email\n"unfinished\n','csv_parse'),(b'email\n\xff\n','csv_encoding'),
    (b'email\n\x00\n','csv_empty'),(b'email,email\na,b\n','csv_headers')])
def test_malformed_csv(content,code):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc: parse_csv(content)
    assert exc.value.detail['code']==code

@pytest.mark.parametrize('delimiter',[',',';'])
def test_bom_quoted_delimiter_newline(delimiter):
    content=f'\ufeffemail{delimiter}name\r\na@example.test{delimiter}"A{delimiter} B\nsecond ""line"""\r\n'.encode()
    columns,rows=parse_csv(content)
    assert columns==['email','name'] and rows[0]['name']==f'A{delimiter} B\nsecond "line"'

def test_ten_thousand_import_and_limit():
    headers=credentials('operator')
    body=('email\n'+''.join(f'load{i}@example.test\n' for i in range(10000))).encode()
    r=client.post('/api/v1/imports',headers=headers,files={'file':('load.csv',body,'text/csv')})
    assert r.status_code==201
    path='/api/v1/imports/'+r.json()['id']
    r=client.post(path+'/analyze',headers=headers);assert r.status_code==200 and r.json()['valid']==10000
    for _ in range(2):
        r=client.post(path+'/commit',headers=headers);assert r.status_code==200 and r.json()['inserted']==10000
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Lead))==10000
        assert db.scalar(select(func.count()).select_from(Event))==1
    r=client.post('/api/v1/imports',headers=headers,files={'file':('over.csv',body+b'over@example.test\n','text/csv')})
    assert r.status_code==413 and r.json()['detail']['code']=='csv_limit'

def test_four_parallel_imports():
    headers=credentials('operator')
    def run(n):
        r=client.post('/api/v1/imports',headers=headers,files={'file':('parallel.csv',f'email\np{n}@example.test\n'.encode(),'text/csv')});assert r.status_code==201
        path='/api/v1/imports/'+r.json()['id']
        assert client.post(path+'/analyze',headers=headers).status_code==200
        assert client.post(path+'/commit',headers=headers).status_code==200
        return r.json()['id']
    with ThreadPoolExecutor(max_workers=4) as pool: ids=list(pool.map(run,range(4)))
    with SessionLocal() as db:
        assert len(set(ids))==4 and db.scalar(select(func.count()).select_from(Lead))==4
        assert db.scalar(select(func.count()).select_from(Event))==4

@pytest.mark.parametrize('filename,mime,body,status',[
    ('bad.txt','text/csv',b'email\na@x.test\n',422),('bad.csv','image/png',b'email\na@x.test\n',422),
    ('bad.csv','text/csv',b'x'*(5*1024*1024+1),413),('bad.csv','text/csv',b'x'*(6*1024*1024+1),413)],ids=['extension','mime','file-size','body-size'])
def test_upload_limits_and_no_persisted_failures(filename,mime,body,status):
    r=client.post('/api/v1/imports',headers=credentials(),files={'file':(filename,body,mime)})
    assert r.status_code==status
    with SessionLocal() as db: assert db.scalar(select(func.count()).select_from(Import))==0

def test_chunked_body_bound_without_content_length():
    from app.request_limit import UploadBodyLimit
    import asyncio
    async def run():
        messages=[];called=[];chunks=iter([{'type':'http.request','body':b'123','more_body':True},{'type':'http.request','body':b'456','more_body':False}])
        async def receive(): return next(chunks)
        async def send(message): messages.append(message)
        async def downstream(*args): called.append(True)
        await UploadBodyLimit(downstream,limit=5)({'type':'http','method':'POST','path':'/api/v1/imports','headers':[]},receive,send)
        assert not called and messages[0]['status']==413
    asyncio.run(run())

@pytest.mark.parametrize('behavior',['rate_limit','timeout','malformed'])
def test_telegram_additional_boundary(queue,monkeypatch,behavior):
    monkeypatch.setenv('ASTRASYNQ_CREDENTIAL_TEST','123456:'+('a'*30))
    def http(*args):
        if behavior=='timeout': raise TimeoutError('private token')
        return (429,b'{"ok":false,"parameters":{"retry_after":2}}') if behavior=='rate_limit' else (200,b'not-json')
    monkeypatch.setattr('app.automation.post',http)
    with SessionLocal() as db:
        cfg=db.get(IntegrationConfig,queue[1]);cfg.kind='telegram';cfg.destination='-123'
        assert send(cfg,db.get(Event,queue[2]))==(None,'timeout') if behavior=='timeout' else send(cfg,db.get(Event,queue[2]))==((429,'http_non_2xx') if behavior=='rate_limit' else (200,'telegram_rejected'))

def test_dns_rebinding_pins_connection(monkeypatch):
    monkeypatch.setenv('ASTRASYNQ_MODE','production')
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,1,6,'',('8.8.8.8',443))])
    parsed,ip,port=resolve_url('https://receiver.example/hook')
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,1,6,'',('127.0.0.1',443))])
    called=[];sentinel=object()
    monkeypatch.setattr(socket,'create_connection',lambda address,timeout:called.append(address) or sentinel)
    conn=PinnedHTTPS(parsed.hostname,ip,port,1)
    class TLS:
        def wrap_socket(self,sock,server_hostname): assert sock is sentinel and server_hostname=='receiver.example';return sentinel
    conn._context=TLS();conn.connect()
    assert called==[('8.8.8.8',443)]

@pytest.mark.parametrize('ip',['::ffff:127.0.0.1','fc00::1','fe80::1','100.64.0.1','0.0.0.0','192.168.1.1'])
def test_private_resolution_regression(monkeypatch,ip):
    monkeypatch.setenv('ASTRASYNQ_MODE','production')
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',(ip,443))])
    with pytest.raises(ValueError): resolve_url('https://receiver.example')

def test_worker_idle_health_and_metrics(queue):
    assert not worker.live();worker.pulse();assert worker.live()
    r=client.get('/api/v1/automation-metrics',headers=credentials(scope=queue[0])).json()
    assert r['worker_alive'] and r['expired_leases']==0 and r['oldest_due_age_seconds']>=0
    with SessionLocal.begin() as db: db.get(WorkerHeartbeat,worker.WORKER_ID).last_seen=utcnow()-timedelta(seconds=91)
    assert not worker.live()

def test_retention_bounded_keeps_active_failed_and_import_dedupe(queue):
    with SessionLocal.begin() as db:
        cfg=db.get(IntegrationConfig,queue[1]);cfg.enabled=False
        for n in range(5): emit(db,queue[0],'integration.test',f'old:{n}',{},configs=[])
        import_id=emit(db,queue[0],'import.completed','old-import',{},configs=[])
        for e in db.scalars(select(Event)): e.created_at=utcnow()-timedelta(days=100)
        db.get(Job,queue[3]).status='failed';db.get(Delivery,queue[4]).status='failed'
    with SessionLocal.begin() as db: assert cleanup(db,batch=2)['event_histories']==2
    for _ in range(4):
        with SessionLocal.begin() as db: cleanup(db,batch=2)
    with SessionLocal.begin() as db:
        assert db.get(Event,import_id) and db.get(Job,queue[3]).status=='failed'
        assert emit(db,queue[0],'import.completed','old-import',{},configs=[])==import_id
        assert db.scalar(select(func.count()).select_from(Event))==2

@pytest.mark.parametrize('days,batch',[(1,100),(90,0),(90,1001)])
def test_retention_rejects_unbounded_settings(days,batch):
    with SessionLocal() as db:
        with pytest.raises(ValueError): cleanup(db,days,batch)

def server_for(handler):
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    return server,thread

def test_four_worker_processes_drain_large_queue(queue):
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']));captured.append(self.headers['X-AstraSynq-Event-ID']);self.send_response(204);self.end_headers()
        def log_message(self,*args): pass
    server,thread=server_for(Handler);processes=[]
    try:
        with SessionLocal.begin() as db:
            db.get(IntegrationConfig,queue[1]).destination=f'http://127.0.0.1:{server.server_port}/hook'
            for n in range(120): emit(db,queue[0],'integration.test',f'bulk:{n}',{})
        script='from app.worker import tick\nfor _ in range(140):\n if not tick(): break'
        processes=[subprocess.Popen([sys.executable,'-c',script],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for _ in range(4)]
        for process in processes: assert process.wait(timeout=45)==0
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(Delivery).where(Delivery.status=='delivered'))==121
            assert db.scalar(select(func.max(Delivery.attempts)))==1
        assert len(captured)==len(set(captured))==121
    finally:
        for process in processes:
            if process.poll() is None: process.kill();process.wait()
        server.shutdown();server.server_close();thread.join(timeout=2)

def test_kill_worker_during_delivery_and_recover_same_event(queue):
    entered=threading.Event();release=threading.Event();captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']));captured.append(self.headers['X-AstraSynq-Event-ID'])
            if len(captured)==1: entered.set();release.wait(15)
            self.send_response(204);self.end_headers()
        def log_message(self,*args): pass
    server,thread=server_for(Handler);process=None
    try:
        with SessionLocal.begin() as db: db.get(IntegrationConfig,queue[1]).destination=f'http://127.0.0.1:{server.server_port}/hook'
        process=subprocess.Popen([sys.executable,'-m','app.worker','--once'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert entered.wait(10);process.kill();process.wait(timeout=5);release.set()
        with SessionLocal.begin() as db: db.get(Job,queue[3]).lease_until=utcnow()-timedelta(seconds=1)
        result=subprocess.run([sys.executable,'-m','app.worker','--once'],capture_output=True,text=True,timeout=15)
        assert result.returncode==0
        with SessionLocal() as db: assert db.get(Delivery,queue[4]).status=='delivered' and db.get(Delivery,queue[4]).attempts==2
        assert captured==[str(queue[2]),str(queue[2])]
    finally:
        release.set()
        if process and process.poll() is None: process.kill();process.wait()
        server.shutdown();server.server_close();thread.join(timeout=2)

@pytest.mark.parametrize('behavior',['500','timeout','slow_success'])
def test_real_webhook_faults(queue,behavior):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            if behavior=='timeout': time.sleep(1.4)
            if behavior=='slow_success': time.sleep(.2)
            self.send_response(500 if behavior=='500' else 204);self.end_headers()
        def log_message(self,*args): pass
    server,thread=server_for(Handler)
    try:
        with SessionLocal.begin() as db:
            cfg=db.get(IntegrationConfig,queue[1]);cfg.destination=f'http://127.0.0.1:{server.server_port}/hook';cfg.timeout=1
        assert worker.process_one()
        with SessionLocal() as db:
            d=db.get(Delivery,queue[4]);assert d.status==('delivered' if behavior=='slow_success' else 'retry')
            assert d.last_error==('timeout' if behavior=='timeout' else 'http_non_2xx' if behavior=='500' else None)
    finally: server.shutdown();server.server_close();thread.join(timeout=2)

def test_database_connection_loss_reconnect():
    # Terminate a dedicated checked-out test connection; pool_pre_ping replaces it on reuse.
    connection=engine.connect();pid=connection.scalar(text('SELECT pg_backend_pid()'));connection.commit()
    with engine.begin() as control: control.execute(text('SELECT pg_terminate_backend(:pid)'),{'pid':pid})
    with pytest.raises(Exception): connection.execute(text('SELECT 1'))
    connection.close()
    with engine.connect() as recovered: assert recovered.scalar(text('SELECT 1'))==1

def test_api_killed_during_commit_then_restart_and_retry():
    import httpx
    from app.models import Workspace
    headers=credentials('operator')
    r=client.post('/api/v1/imports',headers=headers,files={'file':('restart.csv',b'email\nrestart@example.test\n','text/csv')})
    path='/api/v1/imports/'+r.json()['id'];ident=UUID(r.json()['id'])
    assert client.post(path+'/analyze',headers=headers).status_code==200
    with SessionLocal() as db: key=db.get(Import,ident).workspace_id
    # Bind an ephemeral loopback API port and retain ownership of every spawned process.
    with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    process=None
    def start():
        process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            if process.poll() is not None: raise AssertionError('QA API exited')
            try:
                if httpx.get(base+'/health/ready',timeout=1).status_code==200: return process
            except httpx.HTTPError: pass
            time.sleep(.1)
        process.kill();process.wait();raise AssertionError('QA API not ready')
    def commit_request():
        try: return httpx.post(base+path+'/commit',headers=headers,timeout=15).status_code
        except httpx.HTTPError: return 'interrupted'
    try:
        process=start()
        with SessionLocal.begin() as lock:
            lock.scalar(select(Workspace).where(Workspace.id==key).with_for_update())
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(commit_request)
                blocked=False
                for _ in range(100):
                    with engine.connect() as observer:
                        blocked=bool(observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query ILIKE '%workspaces%FOR UPDATE%'")))
                    if blocked: break
                    time.sleep(.05)
                assert blocked,'Commit never reached database lock'
                process.kill();process.wait(timeout=5)
                assert future.result(timeout=5)=='interrupted'
        with SessionLocal() as db:
            assert db.get(Import,ident).status=='analyzed'
            assert db.scalar(select(func.count()).select_from(Lead))==0
            assert db.scalar(select(func.count()).select_from(Event))==0
        process=start()
        for _ in range(2): assert httpx.post(base+path+'/commit',headers=headers,timeout=15).json()['inserted']==1
        process.kill();process.wait(timeout=5);process=start()
        assert httpx.get(base+path,headers=headers).json()['status']=='completed'
        assert httpx.post(base+path+'/commit',headers=headers).json()['inserted']==1
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(Lead))==1
            assert db.scalar(select(func.count()).select_from(Event))==1
    finally:
        if process and process.poll() is None: process.kill();process.wait(timeout=5)
