"""Public sandbox boundaries on isolated PostgreSQL; ordinary suites run non-demo."""
import os, subprocess, sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, func, delete
from app.main import app
from app.database import SessionLocal
from app.models import Workspace, User, Membership, Import, Lead, Delivery, Job, AuditLog, utcnow
from app.config import validate_environment
from app.demo import seed, SAMPLE, SCOPE, EMAIL, accept_sample, reserve_request
from app.auth import attempts
from app.automation import send, post
from auth_helpers import credentials

PASSWORD='Synthetic isolated test password 42!'

@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setenv('ASTRASYNQ_DEMO_MODE','true')
    with SessionLocal.begin() as db:
        db.execute(delete(AuditLog).where(AuditLog.action=='demo.request'))
        seed(db,PASSWORD)
    with TestClient(app) as client:
        pre=client.get('/api/v1/auth/csrf').json()['csrf_token']
        r=client.post('/api/v1/auth/login',headers={'X-CSRF-Token':pre},json={'email':EMAIL,'password':PASSWORD})
        assert r.status_code==200
        client.headers['X-CSRF-Token']=r.json()['csrf_token']
        yield client
    with SessionLocal.begin() as db: db.execute(delete(AuditLog).where(AuditLog.action=='demo.request'))

def test_sample_rejects_real_input():
    accept_sample(SAMPLE.read_bytes())
    for body in (b'email\nreal@company.com\n',SAMPLE.read_bytes()+b'extra',SAMPLE.read_bytes().replace(b'Synthetic',b'Personal')):
        with pytest.raises(HTTPException): accept_sample(body)

def test_recruiter_flow_and_mock_sink(sandbox,monkeypatch):
    def network_forbidden(*args,**kwargs): raise AssertionError('network called')
    monkeypatch.setattr('app.automation.post',network_forbidden)
    r=sandbox.post('/api/v1/imports',files={'file':('arbitrary-personal-name.csv',SAMPLE.read_bytes(),'text/csv')})
    assert r.status_code==201 and r.json()['filename']=='synthetic-demo.csv'
    path='/api/v1/imports/'+r.json()['id']
    assert sandbox.post(path+'/analyze').status_code==200
    assert sandbox.post(path+'/commit').status_code==200
    assert sandbox.post(path+'/commit').status_code==200
    assert sandbox.get('/api/v1/leads').json()['total']==4
    deliveries=sandbox.get('/api/v1/deliveries').json()['items']
    assert len(deliveries)==2
    assert all(d['status']=='delivered' and d['last_response']=='synthetic_sink' and d['response_code'] is None for d in deliveries)
    assert sandbox.get('/api/v1/automation-metrics').json()['worker_alive'] is False
    assert sandbox.get('/api/v1/audit-logs').status_code==200
    assert sandbox.get('/api/v1/samples/leads.csv').content==SAMPLE.read_bytes()

@pytest.mark.parametrize('method,path',[
    ('POST','/api/v1/users'),('PUT','/api/v1/integrations/webhook'),
    ('POST','/api/v1/integrations/webhook/test'),('PUT','/api/v1/automations/daily-summary'),
    ('POST','/api/v1/demo/reset'),('DELETE','/api/v1/imports'),
    ('POST','/api/v1/deliveries/00000000-0000-4000-8000-000000000001/retry')])
def test_sensitive_operations_disabled(sandbox,method,path):
    assert sandbox.request(method,path,json={}).status_code==403

def test_scope_and_csrf_unchanged(sandbox):
    foreign=credentials('operator')
    assert sandbox.get('/api/v1/leads',headers=foreign).status_code==403
    body={'file':('demo.csv',SAMPLE.read_bytes(),'text/csv')}
    assert sandbox.post('/api/v1/imports',headers={'X-CSRF-Token':'wrong'},files=body).status_code==403
    assert sandbox.post('/api/v1/imports',headers={'Origin':'https://evil.example.test'},files=body).status_code==403
    assert sandbox.get('/api/v1/leads').headers['x-astrasynq-mode']=='synthetic-demo'

def test_seed_idempotent_and_scoped_reset(sandbox):
    with SessionLocal.begin() as db:
        assert seed(db,PASSWORD) is False
        assert seed(db,PASSWORD,reset=True) is True
        assert db.scalar(select(func.count()).select_from(User))==1
        assert db.scalar(select(Membership.role))=='operator'
        assert db.scalar(select(func.count()).select_from(Lead))==2
    assert sandbox.get('/api/v1/leads').status_code==401
    credentials('operator')
    with SessionLocal.begin() as db:
        with pytest.raises(RuntimeError): seed(db,PASSWORD,reset=True)

def test_no_seed_in_standard_mode(monkeypatch):
    monkeypatch.delenv('ASTRASYNQ_DEMO_MODE',raising=False)
    with SessionLocal.begin() as db:
        with pytest.raises(RuntimeError): seed(db,PASSWORD)

def test_egress_and_daemon_disabled(sandbox):
    assert send(SimpleNamespace(),SimpleNamespace())==(None,'demo_egress_disabled')
    with pytest.raises(ValueError): post('https://example.test',b'',{},1)
    result=subprocess.run([sys.executable,'-m','app.worker','--once'],capture_output=True,text=True,timeout=15)
    assert result.returncode!=0 and 'no persistent worker' in result.stderr

def test_durable_global_request_budget(sandbox):
    with SessionLocal.begin() as db:
        db.execute(delete(AuditLog).where(AuditLog.action=='demo.request'))
        db.add_all([AuditLog(action='demo.request',entity='sandbox') for _ in range(120)])
    assert sandbox.get('/api/v1/leads').status_code==429
    assert sandbox.get('/health/live').status_code==200

def test_daily_budget_and_restart_survival(sandbox):
    with SessionLocal.begin() as db:
        db.execute(delete(AuditLog).where(AuditLog.action=='demo.request'))
        db.add_all([AuditLog(action='demo.request',entity='sandbox',created_at=utcnow()-timedelta(hours=2)) for _ in range(2000)])
    # A fresh client/process uses the same durable DB counts.
    with TestClient(app) as fresh:
        assert fresh.get('/api/v1/auth/csrf').status_code==429
        assert fresh.get('/health/ready').status_code==429

def test_reservation_lock_and_database_failure(sandbox,monkeypatch):
    from sqlalchemy import text
    with SessionLocal.begin() as db:
        db.execute(text('SELECT pg_advisory_xact_lock(504205042)'))
        assert sandbox.get('/api/v1/leads').status_code==429
    def unavailable(*args,**kwargs): raise RuntimeError('private credentials must not leak')
    monkeypatch.setattr('app.demo.reserve_request',unavailable)
    r=sandbox.get('/api/v1/leads')
    assert r.status_code==500 and 'private credentials' not in r.text

def test_demo_admin_bootstrap_disabled(sandbox):
    result=subprocess.run([sys.executable,'-m','app.bootstrap_admin'],capture_output=True,text=True,timeout=15)
    assert result.returncode!=0 and 'forbids admin bootstrap' in result.stderr

def test_total_import_cap_and_pii_rejection(sandbox):
    r=sandbox.post('/api/v1/imports',files={'file':('real.csv',b'email\nreal@company.com\n','text/csv')})
    assert r.status_code==422
    with SessionLocal.begin() as db:
        db.add_all([Import(workspace_id=SCOPE,filename='synthetic-demo.csv',columns=[],mapping={},total=0) for _ in range(29)])
    assert sandbox.post('/api/v1/imports',files={'file':('demo.csv',SAMPLE.read_bytes(),'text/csv')}).status_code==429

@pytest.mark.parametrize('override',[
    {'ASTRASYNQ_MODE':'development'}, {'ASTRASYNQ_CREDENTIAL_TELEGRAM':'synthetic-value'},
    {'ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS':'true'}, {'ASTRASYNQ_DEMO_MODE':'maybe'},
    {'ASTRASYNQ_DEMO_PASSWORD':'short'}, {'AUTH_SESSION_HOURS':'12'},
    {'AUTH_COOKIE_SECURE':'false'}, {'AUTH_COOKIE_SAMESITE':'none'}])
def test_demo_production_guards(override):
    env=dict(ASTRASYNQ_MODE='production',ASTRASYNQ_DEMO_MODE='true',ASTRASYNQ_DEMO_PASSWORD=PASSWORD,
        AUTH_SESSION_HOURS='1',AUTH_COOKIE_SECURE='true',AUTH_ALLOWED_ORIGINS='https://demo.example.test',
        DATABASE_URL='postgresql://demo:synthetic-long-password@db/demo')
    validate_environment(env)
    env.update(override)
    with pytest.raises(RuntimeError):validate_environment(env)

def test_demo_body_limit_fresh_process():
    env={**os.environ,'ASTRASYNQ_DEMO_MODE':'true'}
    script="from app.main import app;from fastapi.testclient import TestClient;c=TestClient(app);r=c.post('/api/v1/auth/login',content=b'x'*17000);assert r.status_code==413"
    result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
