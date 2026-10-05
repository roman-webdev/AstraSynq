import csv
import io
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

from auth_helpers import credentials

@pytest.fixture
def headers(): return credentials(seed_data=True)

def upload(headers,content=None):
    content=content or (Path(__file__).parents[1]/'samples'/'leads.csv').read_bytes()
    response=client.post('/api/v1/imports',headers=headers,files={'file':('test.csv',content,'text/csv')})
    assert response.status_code==201,response.text
    return response.json()

def test_health_and_openapi():
    assert client.get('/health/live').json()['status']=='ok'
    assert client.get('/health/ready').status_code==200
    schema=client.get('/openapi.json').json()
    assert schema['info']['title']=='AstraSynq API'
    assert schema['paths']['/api/v1/imports']['post']['requestBody']
    assert '200' in schema['paths']['/api/v1/auth/login']['post']['responses']

def test_sample_download():
    response=client.get('/api/v1/samples/leads.csv')
    assert response.status_code==200
    assert len(list(csv.DictReader(io.StringIO(response.text))))==12

def test_full_import_and_idempotent_commit(headers):
    item=upload(headers)
    assert item['status']=='uploaded'
    route=f"/api/v1/imports/{item['id']}"
    result=client.post(route+'/analyze',headers=headers).json()
    assert (result['total'],result['valid'],result['invalid'],result['duplicate'])==(12,8,2,2)
    assert all(r['issues'] for r in result['rows'] if r['classification']!='valid')
    first=client.post(route+'/commit',headers=headers)
    assert first.status_code==200 and first.json()['inserted']==8
    assert client.post(route+'/commit',headers=headers).json()==first.json()
    summary=client.get('/api/v1/dashboard/summary',headers=headers).json()
    assert summary['record_count']==248 and summary['import_count']==7
    assert summary['valid']+summary['invalid']+summary['duplicate']==282
    assert client.put(route+'/mapping',headers=headers,json={'fields':{'email':'email'}}).status_code==409
    assert client.post(route+'/analyze',headers=headers).status_code==409

def test_repeat_file_detects_existing_records(headers):
    first=upload(headers)
    route=f"/api/v1/imports/{first['id']}"
    client.post(route+'/analyze',headers=headers)
    client.post(route+'/commit',headers=headers)
    second=upload(headers)
    result=client.post(f"/api/v1/imports/{second['id']}/analyze",headers=headers).json()
    assert (result['valid'],result['invalid'],result['duplicate'])==(0,2,10)

def test_isolation(headers):
    item=upload(headers)
    other=credentials()
    assert client.get(f"/api/v1/imports/{item['id']}",headers=other).status_code==404
    assert client.get('/api/v1/dashboard/summary',headers=other).json()['record_count']==0

def test_mapping_custom_columns(headers):
    item=upload(headers,b'contact;display_name\nnew@example.com;"Alex; Morgan"\n')
    route=f"/api/v1/imports/{item['id']}"
    assert client.post(route+'/analyze',headers=headers).status_code==422
    response=client.put(route+'/mapping',headers=headers,json={'fields':{'email':'contact','name':'display_name'}})
    assert response.status_code==200
    result=client.post(route+'/analyze',headers=headers).json()
    assert result['valid']==1 and result['rows'][0]['data']['name']=='Alex; Morgan'

@pytest.mark.parametrize('content',[b'',b'a,a\n1,2',b'email,name\nx@example.com,a,b',b'email,name\nx@example.com',b'email\n',b'email\n\xff'])
def test_reject_malformed_csv(headers,content):
    response=client.post('/api/v1/imports',headers=headers,files={'file':('test.csv',content,'text/csv')})
    assert response.status_code==422

def test_limits_and_extension(headers):
    assert client.post('/api/v1/imports',headers=headers,files={'file':('a.txt',b'email\na@example.com')}).status_code==422
    assert client.post('/api/v1/imports',headers=headers,files={'file':('a.csv',b'x'*(5*1024*1024+1))}).status_code==413
    assert client.post('/api/v1/imports',headers=headers,files={'file':('a.csv',b'email\n'+b'a@example.com\n'*10001)}).status_code==413

def test_invalid_mapping_and_state(headers):
    item=upload(headers)
    route=f"/api/v1/imports/{item['id']}"
    assert client.post(route+'/commit',headers=headers).status_code==409
    assert client.get(route+'/issues.csv',headers=headers).status_code==409
    for fields in [{},{'email':'missing'},{'email':'email','name':'email'},{'unsupported':'email'}]:
        assert client.put(route+'/mapping',headers=headers,json={'fields':fields}).status_code==422
    client.cookies.clear()
    assert client.get('/api/v1/dashboard/summary').status_code==401
    assert client.get('/api/v1/dashboard/summary',headers={'X-Demo-Session':'bad'}).status_code==401

def test_recheck_after_workspace_change(headers):
    a,b=upload(headers),upload(headers)
    for item in [a,b]:
        client.post(f"/api/v1/imports/{item['id']}/analyze",headers=headers)
    client.post(f"/api/v1/imports/{a['id']}/commit",headers=headers)
    assert client.post(f"/api/v1/imports/{b['id']}/commit",headers=headers).status_code==409
    assert client.get(f"/api/v1/imports/{b['id']}",headers=headers).json()['valid']==0

def test_export_and_issue_report(headers):
    item=upload(headers,b'email,name,amount,currency,created_at\nnew@example.com,=1+1,NaN,USD,not-a-date\nother@example.com,=1+1,20,USD,\n')
    route=f"/api/v1/imports/{item['id']}"
    result=client.post(route+'/analyze',headers=headers).json()
    assert result['valid']==1 and result['invalid']==1
    report=client.get(route+'/issues.csv',headers=headers)
    assert 'negative_amount' in report.text and 'invalid_date' in report.text
    client.post(route+'/commit',headers=headers)
    export=client.get('/api/v1/leads/export.csv',headers=headers)
    assert "'=1+1" in export.text
    assert len(list(csv.DictReader(io.StringIO(export.text))))==241

def test_contract_only_endpoints(headers):
    assert client.post('/api/v1/auth/login',json={'email':'a@example.com','password':'password'}).status_code==403
    assert client.get('/api/v1/jobs/123',headers=headers).status_code==422

@pytest.mark.parametrize('code,record',[
    ('invalid_email',{'email':'broken'}),
    ('negative_amount',{'email':'new@example.com','amount':'-1','currency':'USD'}),
    ('duplicate_record',{'email':'existing@example.com'}),
    ('required_field',{'email':'new@example.com','amount':'20'}),
    ('invalid_date',{'email':'new@example.com','created_at':'bad-date'}),
    ('invalid_currency',{'email':'new@example.com','currency':'ZZZ'}),
])
def test_validation_codes_have_no_user_text(code,record):
    from app.imports import classify
    result=classify([record],{key:key for key in record},{'existing@example.com'})
    assert code in {issue['code'] for issue in result[0]['issues']}
    assert all(set(issue)=={'field','code'} for issue in result[0]['issues'])

def test_csv_errors_use_codes(headers):
    response=client.post('/api/v1/imports',headers=headers,files={'file':('empty.csv',b'','text/csv')})
    assert response.status_code==422
    assert response.json()['detail']=={'code':'csv_empty'}

