import hashlib, hmac, json, os, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,text
from app.main import app
from app.database import SessionLocal,engine
from app.models import Workspace,Event,Job,Delivery,IntegrationConfig,Schedule,Import,AuditLog,utcnow
from app.automation import emit,signature,send,resolve_url,next_daily,schedule_due
from app import worker
from auth_helpers import credentials
client=TestClient(app)
REF='ASTRASYNQ_CREDENTIAL_TEST'

@pytest.fixture
def queue(monkeypatch):
    monkeypatch.setenv('ASTRASYNQ_MODE','development');monkeypatch.setenv('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS','true');monkeypatch.setenv(REF,'local synthetic signing secret')
    key=uuid4()
    with SessionLocal.begin() as db:
        db.add(Workspace(id=key));db.flush()
        c=IntegrationConfig(workspace_id=key,kind='webhook',enabled=True,destination='http://127.0.0.1:9999/hook',credential_ref=REF,max_attempts=3,backoff=2)
        db.add(c);db.flush();cid=c.id
        eid=emit(db,key,'import.completed','fixture:'+str(key),dict(import_id=str(uuid4()),status='completed',total=2,inserted=1,invalid=1,duplicate=0))
        j=db.scalar(select(Job).where(Job.delivery_id.is_not(None)));jid=j.id;did=j.delivery_id
    return key,cid,eid,jid,did

def due(jid):
    with SessionLocal.begin() as db: db.get(Job,jid).run_after=utcnow()-timedelta(seconds=1)

def test_concurrent_claim_no_double_processing(queue):
    with ThreadPoolExecutor(max_workers=8) as pool: claims=list(pool.map(lambda _:worker.claim(),range(8)))
    assert sum(c is not None for c in claims)==1
    with SessionLocal() as db: assert db.get(Job,queue[3]).attempts==1

def test_skip_locked(queue):
    with SessionLocal.begin() as db:
        db.scalar(select(Job).where(Job.id==queue[3]).with_for_update())
        with ThreadPoolExecutor() as pool: assert pool.submit(worker.claim).result(timeout=5) is None

def test_lease_recovery_and_stale_fencing(queue):
    old=worker.claim()
    with SessionLocal.begin() as db: db.get(Job,old[0]).lease_until=utcnow()-timedelta(seconds=1)
    new=worker.claim();assert new[0]==old[0] and new[1]!=old[1]
    assert not worker.heartbeat(*old)
    assert not worker.finish(*old,200,None)
    assert worker.heartbeat(*new)
    assert worker.finish(*new,200,None)
    with SessionLocal() as db: assert db.get(Delivery,queue[4]).attempts==2

@pytest.mark.parametrize('error',['http_non_2xx','timeout','credential_missing'])
def test_retry_backoff_and_terminal_failure(queue,error):
    for attempt in range(1,4):
        claim=worker.claim();before=utcnow();assert worker.finish(*claim,500,error)
        with SessionLocal() as db:
            j=db.get(Job,queue[3]);d=db.get(Delivery,queue[4]);assert j.attempts==attempt and d.attempts==attempt
            if attempt<3:
                assert j.status=='retry';assert (j.run_after-before).total_seconds()>=2*2**(attempt-1)
            else: assert j.status==d.status=='failed'
        due(queue[3])
    with SessionLocal() as db: assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=='delivery.failed'))==1

def test_exhausted_crash_recovery(queue):
    with SessionLocal.begin() as db:
        j=db.get(Job,queue[3]);j.status='running';j.attempts=3;j.lease_until=utcnow()-timedelta(seconds=1)
    assert worker.claim() is None
    with SessionLocal() as db: assert db.get(Job,queue[3]).status=='failed'

def test_idempotent_event_and_atomic_rollback(queue):
    key,cid,eid,jid,did=queue
    with SessionLocal.begin() as db:
        assert emit(db,key,'import.completed','fixture:'+str(key),{})==eid
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Event))==1
        assert db.scalar(select(func.count()).select_from(Delivery))==1
    with pytest.raises(RuntimeError):
        with SessionLocal.begin() as db:
            emit(db,key,'import.completed','rollback',{});raise RuntimeError()
    with SessionLocal() as db: assert db.scalar(select(Event).where(Event.dedupe_key=='rollback')) is None

@pytest.mark.parametrize('status',[200,204,400,429,500,503])
def test_webhook_http_boundary(queue,monkeypatch,status):
    captured={}
    def http(url,body,headers,timeout): captured.update(body=body,headers=headers);return status,b'ignored private response'
    monkeypatch.setattr('app.automation.post',http)
    assert worker.process_one()
    with SessionLocal() as db:
        d=db.get(Delivery,queue[4]);assert d.status==('delivered' if status<300 else 'retry');assert d.response_code==status
    h=captured['headers'];expected='sha256='+hmac.new(b'local synthetic signing secret',(h['X-AstraSynq-Timestamp']+'.'+h['X-AstraSynq-Event-ID']+'.').encode()+captured['body'],hashlib.sha256).hexdigest()
    assert h['X-AstraSynq-Signature']==expected;assert h['X-AstraSynq-Event-ID']==str(queue[2])
    assert 'email' not in captured['body'].decode()

def test_timeout(queue,monkeypatch):
    def http(*args): raise TimeoutError('secret must never be recorded')
    monkeypatch.setattr('app.automation.post',http);worker.process_one()
    with SessionLocal() as db: assert db.get(Delivery,queue[4]).last_error=='timeout'

@pytest.mark.parametrize('status,response,error',[(200,b'{"ok":true}',None),(200,b'{"ok":false}','telegram_rejected'),(401,b'{"description":"token"}','http_non_2xx'),(500,b'error','http_non_2xx')])
def test_telegram_http_boundary(queue,monkeypatch,status,response,error):
    monkeypatch.setenv(REF,'123456:'+('a'*30));captured={}
    def http(url,body,headers,timeout): captured.update(url=url,body=json.loads(body));return status,response
    monkeypatch.setattr('app.automation.post',http)
    with SessionLocal() as db:
        c=db.get(IntegrationConfig,queue[1]);c.kind='telegram';c.destination='-123';e=db.get(Event,queue[2]);assert send(c,e)==(status,error)
    assert captured['url'].endswith('/sendMessage');assert captured['body']['chat_id']=='-123';assert 'email' not in captured['body']['text']

@pytest.mark.parametrize('url',['http://8.8.8.8','https://127.0.0.1','https://10.0.0.1','https://169.254.169.254','https://[::1]','https://user:pass@example.com','https://example.com?q=secret'])
def test_production_ssrf(url,monkeypatch):
    monkeypatch.setenv('ASTRASYNQ_MODE','production');monkeypatch.setenv('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS','true')
    with pytest.raises(ValueError): resolve_url(url)

def test_mixed_dns_blocked_and_pin(monkeypatch):
    monkeypatch.setenv('ASTRASYNQ_MODE','production')
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError): resolve_url('https://receiver.example/hook')

def test_daily_summary(queue):
    key=queue[0];now=utcnow()
    with SessionLocal.begin() as db:
        s=Schedule(workspace_id=key,enabled=True,timezone='Europe/Kyiv',next_run_at=now-timedelta(seconds=1));db.add(s);db.flush();sid=s.id
        schedule_due(db,now);schedule_due(db,now)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Event).where(Event.type=='summary.daily'))==1
        assert db.get(Schedule,sid).next_run_at>now
    from datetime import datetime,timezone
    for date in [datetime(2026,3,28,12,tzinfo=timezone.utc),datetime(2026,10,24,12,tzinfo=timezone.utc)]:
        assert next_daily(date,'Europe/Kyiv').astimezone(__import__('zoneinfo').ZoneInfo('Europe/Kyiv')).hour==9

def test_manual_retry_preserves_event_and_lifetime_attempts(queue):
    h=credentials('operator',queue[0])
    with SessionLocal.begin() as db:
        db.get(Job,queue[3]).status='failed';db.get(Job,queue[3]).attempts=3;db.get(Delivery,queue[4]).status='failed';db.get(Delivery,queue[4]).attempts=3
    assert client.post(f'/api/v1/deliveries/{queue[4]}/retry',headers=h).status_code==202
    assert client.post(f'/api/v1/deliveries/{queue[4]}/retry',headers=h).status_code==409
    with SessionLocal() as db:
        assert db.get(Job,queue[3]).attempts==0;assert db.get(Delivery,queue[4]).attempts==3;assert db.get(Delivery,queue[4]).event_id==queue[2]

@pytest.mark.parametrize('role',['admin','operator','viewer'])
def test_rbac_csrf_scope_secrets(queue,role):
    h=credentials(role,queue[0]);body=dict(enabled=True,destination='http://127.0.0.1:9999',credential_ref=REF)
    for path in ['/integrations','/deliveries','/automations','/automation-metrics']:
        r=client.get('/api/v1'+path,headers=h);assert r.status_code==200;assert 'local synthetic signing secret' not in r.text
    assert client.put('/api/v1/integrations/webhook',headers=h,json=body).status_code==(200 if role=='admin' else 403)
    assert client.put('/api/v1/automations/daily-summary',headers=h,json={'enabled':True,'timezone':'Europe/Kyiv'}).status_code==(200 if role=='admin' else 403)
    assert client.post('/api/v1/integrations/webhook/test',headers=h).status_code==(403 if role=='viewer' else 202)
    assert client.post('/api/v1/integrations/webhook/test',headers={'Cookie':h['Cookie']}).status_code==403
    other=credentials('admin');assert client.get('/api/v1/deliveries',headers=other).json()['items']==[]
    assert client.get(f'/api/v1/jobs/{queue[3]}',headers=other).status_code==404
    assert client.post(f'/api/v1/deliveries/{queue[4]}/retry',headers=other).status_code==404

def test_import_outbox_regression(queue):
    h=credentials('operator',queue[0]);r=client.post('/api/v1/imports',headers=h,files={'file':('fixture.csv',b'email\none@example.test\n')});assert r.status_code==201
    path='/api/v1/imports/'+r.json()['id'];assert client.post(path+'/analyze',headers=h).status_code==200
    for _ in range(2): assert client.post(path+'/commit',headers=h).status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Event).where(Event.dedupe_key=='import:'+r.json()['id']))==1
        assert db.scalar(select(func.count()).select_from(Delivery))==2

def test_process_restart_persistence(queue):
    acquired=worker.claim()
    script='from app.database import SessionLocal;from app.models import Job;from uuid import UUID;import sys;\nwith SessionLocal() as db: print(db.get(Job,UUID(sys.argv[1])).status)'
    result=subprocess.run([sys.executable,'-c',script,str(acquired[0])],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='running'
    with SessionLocal.begin() as db: db.get(Job,acquired[0]).lease_until=utcnow()-timedelta(seconds=1)
    script='from app.worker import claim;print(claim() is not None)'
    assert subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,check=True).stdout.strip()=='True'

def test_separate_worker_smoke_local_webhook(queue):
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.append((self.headers,self.rfile.read(int(self.headers['Content-Length']))));self.send_response(204);self.end_headers()
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with SessionLocal.begin() as db: db.get(IntegrationConfig,queue[1]).destination=f'http://127.0.0.1:{server.server_port}/hook'
        result=subprocess.run([sys.executable,'-m','app.worker','--once'],capture_output=True,text=True,timeout=15,check=True)
        with SessionLocal() as db: assert db.get(Delivery,queue[4]).status=='delivered'
        assert len(captured)==1;assert captured[0][0]['X-AstraSynq-Event-ID']==str(queue[2])
    finally: server.shutdown();server.server_close();thread.join(timeout=2)

def test_migration_downgrade_upgrade():
    from alembic import command
    from alembic.config import Config
    command.downgrade(Config('alembic.ini'),'a3auth0000001')
    with engine.connect() as conn: assert conn.scalar(text("SELECT to_regclass('public.events')")) is None
    command.upgrade(Config('alembic.ini'),'head')
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version"))=='a5release00001'
        for table in ['events','jobs','deliveries','integration_configs','schedules']:
            assert conn.scalar(text("SELECT to_regclass(:table)"),{'table':table})


def test_real_transport_pinning_no_redirect(queue):
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from app.automation import post
    hits=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path);self.rfile.read(int(self.headers['Content-Length']));self.send_response(302);self.send_header('Location','http://169.254.169.254/');self.end_headers()
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        code,_=post(f'http://127.0.0.1:{server.server_port}/hook',b'{}',{},2)
        assert code==302 and hits==['/hook']
    finally: server.shutdown();server.server_close();thread.join(timeout=2)
