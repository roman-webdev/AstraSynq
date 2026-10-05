import csv
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.config import Config
from app.main import app
from app.database import engine, SessionLocal
from app.models import Lead, Import, ImportRow, ValidationIssue
from app.store import seed, DEMO_WORKSPACE

client=TestClient(app)
from auth_helpers import credentials
@pytest.fixture
def headers(): return credentials()

def upload(headers, content=b'email,name,company\nnew@example.com,Test,Orbit\n', name='test.csv'):
    r=client.post('/api/v1/imports',headers=headers,files={'file':(name,content,'text/csv')})
    assert r.status_code==201,r.text
    return '/api/v1/imports/'+r.json()['id']
def analyze(route,headers):
    r=client.post(route+'/analyze',headers=headers);assert r.status_code==200,r.text;return r.json()

def test_migration_schema_and_downgrade_upgrade():
    cfg=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    command.downgrade(cfg,'base')
    assert 'leads' not in inspect(engine).get_table_names()
    assert client.get('/health/ready').status_code==503
    command.upgrade(cfg,'head');command.upgrade(cfg,'head')
    assert {'workspaces','imports','import_rows','validation_issues','leads'} <= set(inspect(engine).get_table_names())
    assert any(x['column_names']==['email_normalized'] for x in inspect(engine).get_unique_constraints('leads'))
    assert len(inspect(engine).get_foreign_keys('leads'))==3
    command.check(cfg)

def test_upload_mapping_and_issues_survive_connection_restart(headers):
    route=upload(headers,b'contact,amount,currency\nBAD,5,USD\nx@example.com,20,USD\nx@example.com,20,USD\n')
    engine.dispose()
    assert client.get(route,headers=headers).json()['total']==3
    r=client.put(route+'/mapping',headers=headers,json={'fields':{'email':'contact','amount':'amount','currency':'currency'}})
    assert r.json()['status']=='mapped'
    engine.dispose();result=analyze(route,headers)
    assert (result['valid'],result['invalid'],result['duplicate'])==(1,1,1)
    engine.dispose()
    assert client.get(route,headers=headers).json()==result
    assert 'invalid_email' in client.get(route+'/issues.csv',headers=headers).text

def test_actual_api_process_restart(headers):
    import urllib.request
    port=8766
    def call(path,method='GET'):
        request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers=headers,method=method)
        with urllib.request.urlopen(request,timeout=3) as r: return json.load(r)
    def start():
        p=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=Path(__file__).parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(60):
            if p.poll() is not None: raise AssertionError('API process failed to start')
            try: call('/health/ready');return p
            except Exception: time.sleep(.1)
        p.terminate();p.wait();raise AssertionError('API did not become ready')
    route=upload(headers,b'email,name\nrestart@example.com,=1+1\nbad,Bad\nrestart@example.com,Duplicate\n')
    analyze(route,headers)
    p=start()
    try:
        committed=call(route+'/commit','POST')
        before=call(route);metrics=call('/api/v1/dashboard/summary');identity=call('/api/v1/auth/me')
    finally: p.terminate();p.wait(timeout=10)
    with pytest.raises(Exception): call('/health/ready')
    p=start()
    try:
        assert call(route)==before
        assert call('/api/v1/dashboard/summary')==metrics
        assert call('/api/v1/auth/me')==identity
        assert call(route+'/commit','POST')==committed
        assert (before['valid'],before['invalid'],before['duplicate'])==(1,1,1)
    finally: p.terminate();p.wait(timeout=10)

def test_global_duplicates_invalid_priority(headers):
    route=upload(headers);analyze(route,headers);client.post(route+'/commit',headers=headers)
    other=credentials()
    second=upload(other,b'email,amount,currency\n NEW@EXAMPLE.COM ,NaN,USD\nnew@example.com,20,USD\nfresh@example.com,1,USD\nFRESH@example.com,2,USD\n')
    result=analyze(second,other)
    assert (result['total'],result['valid'],result['invalid'],result['duplicate'])==(4,1,1,2)
    assert result['rows'][0]['classification']=='invalid'
    assert not any(i['code']=='duplicate_record' for i in result['rows'][0]['issues'])

def test_concurrent_same_import_commit(headers):
    route=upload(headers);analyze(route,headers)
    def commit(_):
        with TestClient(app) as c: return c.post(route+'/commit',headers=headers)
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(commit,range(4)))
    assert all(r.status_code==200 for r in results)
    assert all(r.json()==results[0].json() for r in results)
    with SessionLocal() as db: assert len(list(db.scalars(select(Lead))))==1

def test_concurrent_cross_workspace_commit():
    a,b=credentials(),credentials()
    routes=[upload(h) for h in [a,b]]
    for route,h in zip(routes,[a,b]): analyze(route,h)
    def commit(pair):
        with TestClient(app) as c: return c.post(pair[0]+'/commit',headers=pair[1])
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(commit,zip(routes,[a,b])))
    assert sorted(r.status_code for r in results)==[200,409]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Lead))))==1
        assert sum(i.inserted for i in db.scalars(select(Import)))==1
    loser=next(n for n,r in enumerate(results) if r.status_code==409)
    item=client.get(routes[loser],headers=[a,b][loser]).json()
    assert item['valid']==0 and item['duplicate']==1
    assert client.post(routes[loser]+'/commit',headers=[a,b][loser]).json()['inserted']==0

def test_unique_constraint_direct_writer(headers):
    route=upload(headers);analyze(route,headers);client.post(route+'/commit',headers=headers)
    with SessionLocal() as db:
        lead=db.scalar(select(Lead))
        db.add(Lead(workspace_id=lead.workspace_id,import_id=lead.import_id,email_normalized=lead.email_normalized,data=lead.data))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()

def test_database_partition_constraint(headers):
    route=upload(headers);analyze(route,headers)
    with engine.begin() as conn:
        with pytest.raises(IntegrityError): conn.execute(text('UPDATE imports SET valid=99'))

def test_pagination_filters_stable_sort_and_export(headers):
    for n in range(5):
        route=upload(headers,f'email,name,company\nlead{n}@example.com,Name {n},Orbit\n'.encode(),f'batch-{n}.csv')
        analyze(route,headers);client.post(route+'/commit',headers=headers)
    def get(path): return client.get(path,headers=headers).json()
    first=get('/api/v1/imports?page_size=2');second=get('/api/v1/imports?page_size=2&page=2')
    assert first['total']==5 and len(second['items'])==2
    assert not {i['id'] for i in first['items']} & {i['id'] for i in second['items']}
    assert get('/api/v1/imports?page_size=2')==first
    assert get('/api/v1/imports?search=batch-3&status=completed')['total']==1
    assert get('/api/v1/imports?status=uploaded')['total']==0
    assert get('/api/v1/leads?search=Name%202&company=Orbit')['total']==1
    assert get('/api/v1/leads?company=Missing')['total']==0
    leads=get('/api/v1/leads?page_size=2');assert leads['total']==5
    assert get('/api/v1/leads?import_id='+leads['items'][0]['import_id'])['total']==1
    export=client.get('/api/v1/leads/export.csv?search=lead2',headers=headers)
    assert len(list(csv.DictReader(io.StringIO(export.text))))==1
    assert client.get('/api/v1/leads?page_size=101',headers=headers).status_code==422
    assert client.get('/api/v1/imports?page=0',headers=headers).status_code==422

def test_literal_search_percent(headers):
    route=upload(headers,name='100%_source.csv')
    assert client.get('/api/v1/imports?search=%25_',headers=headers).json()['total']==1
    assert client.get('/api/v1/imports?search=%25_missing',headers=headers).json()['total']==0

def test_dashboard_counts_database_and_utc(headers):
    route=upload(headers,b'email,created_at\nvalid@example.com,2026-01-01T02:00:00+02:00\nbad,\nvalid@example.com,\n')
    analyze(route,headers)
    assert client.get('/api/v1/dashboard/summary',headers=headers).json()['import_count']==0
    client.post(route+'/commit',headers=headers)
    summary=client.get('/api/v1/dashboard/summary',headers=headers).json()
    assert (summary['record_count'],summary['import_count'],summary['valid'],summary['invalid'],summary['duplicate'])==(1,1,1,1,1)
    assert summary['quality']==33.3 and sum(s['records'] for s in summary['series'])==1
    lead=client.get('/api/v1/leads',headers=headers).json()['items'][0]
    assert lead['data']['created_at']=='2026-01-01T00:00:00+00:00'
    assert lead['created_at'].endswith('+00:00')

def test_seed_idempotent_and_real_rows():
    with SessionLocal.begin() as db: assert seed(db)
    with SessionLocal.begin() as db: assert not seed(db)
    h=credentials(scope=DEMO_WORKSPACE)
    assert client.get('/api/v1/dashboard/summary',headers=h).json()['record_count']==240
    with SessionLocal() as db:
        assert len(list(db.scalars(select(ImportRow))))==270
        assert len(list(db.scalars(select(ValidationIssue))))==30

def test_mapping_clears_persisted_issues(headers):
    route=upload(headers,b'email\nbad\n');analyze(route,headers)
    r=client.put(route+'/mapping',headers=headers,json={'fields':{'email':'email'}})
    assert r.json()['rows']==[] and r.json()['status']=='mapped'
    with SessionLocal() as db: assert not list(db.scalars(select(ValidationIssue)))

def test_csv_formula_prefixes(headers):
    route=upload(headers,b'email,name,company\na@example.com,=1+1,@SUM(1)\nb@example.com,+1,-1\n')
    analyze(route,headers);client.post(route+'/commit',headers=headers)
    content=client.get('/api/v1/leads/export.csv',headers=headers).text
    for value in ["'=1+1","'@SUM(1)","'+1","'-1"]: assert value in content


def test_late_global_collision_rolls_back_entire_commit(headers,monkeypatch):
    from app import persistence
    from app.models import Workspace
    route=upload(headers,b'email\nfirst@example.com\nlate@example.com\n')
    analyze(route,headers)
    original=persistence.analyze_item
    def intervene(db,item):
        rows=original(db,item)
        other=uuid4()
        with SessionLocal.begin() as external:
            external.add(Workspace(id=other));external.flush()
            imported=Import(workspace_id=other,filename='external.csv',columns=['email'],mapping={'email':'email'},total=1,status='completed',valid=1,invalid=0,duplicate=0,inserted=1,committed_at=__import__('app.models',fromlist=['utcnow']).utcnow())
            external.add(imported);external.flush()
            external.add(Lead(workspace_id=other,import_id=imported.id,email_normalized='late@example.com',data={'email':'late@example.com'}))
        monkeypatch.setattr(persistence,'analyze_item',original)
        return rows
    monkeypatch.setattr(persistence,'analyze_item',intervene)
    response=client.post(route+'/commit',headers=headers)
    assert response.status_code==409
    with SessionLocal() as db:
        assert set(db.scalars(select(Lead.email_normalized)))=={'late@example.com'}
    item=client.get(route,headers=headers).json()
    assert (item['valid'],item['duplicate'],item['inserted'])==(1,1,0)
    assert client.post(route+'/commit',headers=headers).json()['inserted']==1
