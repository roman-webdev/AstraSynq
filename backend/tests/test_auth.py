from datetime import timedelta
from uuid import uuid4,UUID
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,inspect,text
from app.main import app
from app.database import SessionLocal,engine
from app.models import User, Membership, AuthSession, AuditLog, Workspace, utcnow
from app.auth import hasher,digest,csrf_for,COOKIE,attempts
from auth_helpers import credentials

PASSWORD='Test only strong password 123!'

def account(role='admin',active=True,member_active=True,scope=None):
    key=scope or uuid4()
    with SessionLocal.begin() as db:
        if not db.get(Workspace,key): db.add(Workspace(id=key));db.flush()
        u=User(email=f'{uuid4()}@example.test',password_hash=hasher.hash(PASSWORD),active=active);db.add(u);db.flush()
        m=Membership(user_id=u.id,workspace_id=key,role=role,active=member_active);db.add(m);db.flush()
        return str(u.id),u.email,key

def login(c,email,password=PASSWORD,**extra):
    token=c.get('/api/v1/auth/csrf').json()['csrf_token']
    return c.post('/api/v1/auth/login',headers={'X-CSRF-Token':token,**extra},json={'email':email,'password':password})

def test_login_me_logout_hashes_and_cookie():
    uid,email,scope=account()
    with TestClient(app) as c:
        r=login(c,email);assert r.status_code==200,r.text
        token=c.cookies.get(COOKIE);csrf=r.json()['csrf_token']
        assert len(token)>=40 and csrf==csrf_for(token)
        cookie=r.headers.get('set-cookie');assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Max-Age=43200' in cookie
        assert c.get('/api/v1/auth/me').json()==r.json()
        with SessionLocal() as db:
            u=db.get(User,UUID(uid));assert u.password_hash.startswith('$argon2id$') and PASSWORD not in u.password_hash
            sess=db.scalar(select(AuthSession));assert sess.token_hash==digest(token) and token not in sess.token_hash
        assert c.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf}).status_code==204
        assert c.get('/api/v1/auth/me').status_code==401
        assert c.get('/api/v1/auth/me',headers={'Cookie':f'{COOKIE}={token}'}).status_code==401
    with SessionLocal() as db:
        assert set(db.scalars(select(AuditLog.action)))=={'login.success','logout'}
        assert db.scalar(select(AuthSession)).revoked_at is not None

@pytest.mark.parametrize('active,member_active,password',[(True,True,'incorrect'),(False,True,PASSWORD),(True,False,PASSWORD)])
def test_invalid_credentials_and_failure_audit(active,member_active,password):
    uid,email,scope=account(active=active,member_active=member_active)
    with TestClient(app) as c:
        r=login(c,email,password);assert r.status_code==401 and r.json()['detail']['code']=='invalid_credentials'
        assert not c.cookies.get(COOKIE)
    with SessionLocal() as db:
        event=db.scalar(select(AuditLog));assert event.action=='login.failure' and str(event.actor_id)==uid and event.workspace_id==scope
        assert not list(db.scalars(select(AuthSession)))

def test_unknown_login_and_sensitive_validation():
    with TestClient(app) as c:
        assert login(c,'unknown@example.test').status_code==401
        secret='secret-value-that-must-not-appear'*20
        r=c.post('/api/v1/auth/login',json={'email':'x','password':secret})
        assert r.status_code==422 and secret not in r.text and 'secret-value' not in r.text
    with SessionLocal() as db:
        e=db.scalar(select(AuditLog));assert e.actor_id is None and e.workspace_id is None

@pytest.mark.parametrize('change',['expiry','revocation','user_inactive','membership_inactive'])
def test_session_invalidated(change):
    uid,email,_=account()
    with TestClient(app) as c:
        assert login(c,email).status_code==200
        with SessionLocal.begin() as db:
            sess=db.scalar(select(AuthSession));member=db.get(Membership,sess.membership_id)
            if change=='expiry': sess.created_at=utcnow()-timedelta(hours=2);sess.expires_at=utcnow()-timedelta(hours=1)
            elif change=='revocation': sess.revoked_at=utcnow()
            elif change=='user_inactive': db.get(User,UUID(uid)).active=False
            else: member.active=False
        assert c.get('/api/v1/auth/me').status_code==401
        assert c.get('/api/v1/leads').status_code==401

def test_login_rotates_previous_session():
    _,email,_=account()
    with TestClient(app) as c:
        login(c,email);old=c.cookies.get(COOKIE);login(c,email);new=c.cookies.get(COOKIE)
        assert old!=new
        assert c.get('/api/v1/auth/me',headers={'Cookie':f'{COOKIE}={old}'}).status_code==401
        assert c.get('/api/v1/auth/me').status_code==200

def test_csrf_login_and_mutations():
    _,email,_=account()
    with TestClient(app) as c:
        assert c.post('/api/v1/auth/login',json={'email':email,'password':PASSWORD}).status_code==403
        assert login(c,email,Origin='https://evil.example').status_code==403
        r=login(c,email);csrf=r.json()['csrf_token']
        for headers in [{},{'X-CSRF-Token':'wrong'},{'X-CSRF-Token':csrf,'Origin':'https://evil.example'},{'X-CSRF-Token':csrf,'Sec-Fetch-Site':'cross-site'}]:
            assert c.post('/api/v1/auth/logout',headers=headers).status_code==403
        assert c.get('/api/v1/auth/me').status_code==200
        assert c.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf,'Origin':'http://127.0.0.1:4174'}).status_code==403
        assert c.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf,'Origin':'http://127.0.0.1:4184'}).status_code==204

@pytest.mark.parametrize('role',['viewer','operator','admin'])
def test_rbac_key_endpoints(role):
    h=credentials(role)
    with TestClient(app) as c:
        for path in ['/dashboard/summary','/imports','/leads','/leads/export.csv','/integrations']:
            assert c.get('/api/v1'+path,headers=h).status_code==200
        for path in ['/users','/api-keys']:
            assert c.get('/api/v1'+path,headers=h).status_code==(200 if role=='admin' else 403)
        assert c.get('/api/v1/audit-logs',headers=h).status_code==(403 if role=='viewer' else 200)
        r=c.post('/api/v1/imports',headers=h,files={'file':('test.csv',b'email\nvalid@example.com\n')})
        assert r.status_code==(403 if role=='viewer' else 201)
        if role!='viewer':
            route='/api/v1/imports/'+r.json()['id']
            assert c.put(route+'/mapping',headers=h,json={'fields':{'email':'email'}}).status_code==200
            assert c.post(route+'/analyze',headers=h).status_code==200
            assert c.post(route+'/commit',headers=h).status_code==200
        assert c.put('/api/v1/integrations/webhook',headers=h,json={'type':'webhook','destination':'https://example.test'}).status_code==(422 if role=='admin' else 403)

def test_viewer_cannot_change_readable_import():
    admin_h=credentials();token=admin_h['Cookie'].split('=',1)[1]
    with SessionLocal() as db: scope=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(token))).workspace_id
    viewer=credentials('viewer',scope)
    with TestClient(app) as c:
        r=c.post('/api/v1/imports',headers=admin_h,files={'file':('test.csv',b'email\nvalid@example.com\n')});route='/api/v1/imports/'+r.json()['id']
        assert c.get(route,headers=viewer).status_code==200
        assert c.put(route+'/mapping',headers=viewer,json={'fields':{'email':'email'}}).status_code==403
        for action in ['analyze','commit']: assert c.post(route+'/'+action,headers=viewer).status_code==403

@pytest.mark.parametrize('role',['viewer','operator','admin'])
def test_admin_user_create_and_update(role):
    h=credentials(role)
    with TestClient(app) as c:
        r=c.post('/api/v1/users',headers=h,json={'email':'new@example.test','password':PASSWORD,'role':'viewer'})
        assert r.status_code==(201 if role=='admin' else 403)
        if role=='admin':
            uid=r.json()['id'];assert 'password' not in r.text
            assert c.put(f'/api/v1/users/{uid}/role',headers=h,json={'role':'operator'}).json()['role']=='operator'
            assert c.post('/api/v1/users',headers=h,json={'email':'new@example.test','password':PASSWORD,'role':'admin'}).status_code==409
        else:
            assert c.put(f'/api/v1/users/{uuid4()}/role',headers=h,json={'role':'admin'}).status_code==403

def test_role_change_revokes_session_last_admin_and_isolation():
    h=credentials();token=h['Cookie'].split('=',1)[1]
    with SessionLocal() as db:
        s=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(token)));m=db.get(Membership,s.membership_id);scope=m.workspace_id;admin_id=m.user_id
    uid,email,_=account(role='viewer',scope=scope)
    other_id,_,other_scope=account()
    with TestClient(app) as c,TestClient(app) as target:
        login(target,email)
        assert c.put(f'/api/v1/users/{uid}/role',headers=h,json={'role':'operator'}).status_code==200
        assert target.get('/api/v1/auth/me').status_code==401
        assert c.put(f'/api/v1/users/{admin_id}/role',headers=h,json={'role':'viewer'}).status_code==409
        assert c.put(f'/api/v1/users/{other_id}/role',headers=h,json={'role':'viewer'}).status_code==404
        assert other_id not in c.get('/api/v1/users',headers=h).text
        assert str(other_scope) not in c.get('/api/v1/audit-logs',headers=h).text

def test_demo_header_is_not_authorization_or_scope():
    with TestClient(app) as c:
        assert c.get('/api/v1/dashboard/summary',headers={'X-Demo-Session':str(uuid4())}).status_code==401
        h=credentials();me=c.get('/api/v1/auth/me',headers=h).json()
        h['X-Demo-Session']=str(uuid4());assert c.get('/api/v1/auth/me',headers=h).json()['workspace_id']==me['workspace_id']
        assert 'x-demo-session' not in str(c.get('/openapi.json').json()).lower()

def test_audit_lifecycle_scope_and_no_secrets():
    h=credentials()
    with TestClient(app) as c:
        r=c.post('/api/v1/imports',headers=h,files={'file':('test.csv',b'email\na@example.test\n')});route='/api/v1/imports/'+r.json()['id']
        c.post(route+'/analyze',headers=h);c.post(route+'/commit',headers=h);c.get('/api/v1/leads/export.csv',headers=h);c.get(route+'/issues.csv',headers=h)
        body=c.get('/api/v1/audit-logs',headers=h).json()
        assert set(e['action'] for e in body['items'])=={'import.analyzed','import.committed','export'}
        assert all(e['actor'] and e['workspace_id'] and e['timestamp'] for e in body['items'])
        assert h['Cookie'].split('=',1)[1] not in str(body) and h['X-CSRF-Token'] not in str(body)
        with SessionLocal() as db: assert not any(PASSWORD in str(e.__dict__) for e in db.scalars(select(AuditLog)))

def test_basic_login_rate_limit():
    with TestClient(app) as c:
        for _ in range(10): assert login(c,'unknown@example.test').status_code==401
        assert login(c,'unknown@example.test').status_code==429

def test_auth_migration_downgrade_preserves_import_tables():
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    cfg=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    command.downgrade(cfg,'6d131c25bdd2')
    tables=set(inspect(engine).get_table_names());assert 'leads' in tables and 'users' not in tables
    command.upgrade(cfg,'head');command.check(cfg)
    assert {'users','workspace_memberships','sessions','audit_logs'}<=set(inspect(engine).get_table_names())

def test_secure_cookie_configuration_over_https(monkeypatch):
    from app import auth
    monkeypatch.setattr(auth,'SECURE',True)
    monkeypatch.setattr(auth,'SAMESITE','strict')
    _,email,_=account()
    with TestClient(app,base_url='https://testserver') as c:
        r=login(c,email);assert r.status_code==200
        cookie=r.headers['set-cookie'];assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
        assert c.get('/api/v1/auth/me').status_code==200
        assert r.headers['cache-control']=='no-store' and r.headers['x-content-type-options']=='nosniff'

def test_bootstrap_hidden_secret_and_safe_idempotency(monkeypatch,capsys):
    from app.bootstrap_admin import main
    scope=uuid4()
    with SessionLocal.begin() as db: db.add(Workspace(id=scope))
    monkeypatch.setenv('ASTRASYNQ_WORKSPACE_ID',str(scope))
    monkeypatch.setenv('ASTRASYNQ_ADMIN_EMAIL','bootstrap@example.test')
    monkeypatch.setenv('ASTRASYNQ_ADMIN_PASSWORD',PASSWORD)
    main();assert PASSWORD not in capsys.readouterr().out
    with SessionLocal() as db:
        u=db.scalar(select(User));assert u.email=='bootstrap@example.test' and hasher.verify(u.password_hash,PASSWORD)
        assert db.scalar(select(Membership)).role=='admin'
    with pytest.raises(SystemExit,match='Active Admin already exists'): main()
    monkeypatch.setenv('ASTRASYNQ_ADMIN_PASSWORD','short')
    with pytest.raises(SystemExit,match='Invalid email/password'): main()
    assert 'short' not in capsys.readouterr().out

