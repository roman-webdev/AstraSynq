"""Opaque server sessions, per-session CSRF and single-membership RBAC."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID
from typing import Literal
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.security import APIKeyCookie, APIKeyHeader
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from .database import SessionLocal, get_db
from .models import User, Membership, AuthSession, AuditLog, Workspace, utcnow

COOKIE = 'astrasynq_session'
PREAUTH_COOKIE = 'astrasynq_login_csrf'
SECURE = os.getenv('AUTH_COOKIE_SECURE','false').lower() == 'true'
SAMESITE = os.getenv('AUTH_COOKIE_SAMESITE','lax').lower()
TTL = int(os.getenv('AUTH_SESSION_HOURS','12'))
ORIGINS = set(os.getenv('AUTH_ALLOWED_ORIGINS','http://127.0.0.1:4184,http://localhost:4184,http://127.0.0.1:8011').split(','))
if SAMESITE not in ('lax','strict') or not 1 <= TTL <= 168:
    raise RuntimeError('Auth requires SameSite lax/strict and session lifetime 1..168 hours')
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
cookie_scheme = APIKeyCookie(name=COOKIE,auto_error=False)
csrf_scheme = APIKeyHeader(name='X-CSRF-Token',auto_error=False)
router = APIRouter(prefix='/api/v1',tags=['auth'])

def fail(status,code): raise HTTPException(status,{'code':code})
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def csrf_for(token): return hmac.new(token.encode(),b'astrasynq.csrf.v1',hashlib.sha256).hexdigest()
def audit(db,actor,scope,action,entity,entity_id=None):
    db.add(AuditLog(actor_id=actor,workspace_id=scope,action=action,entity=entity,entity_id=str(entity_id) if entity_id else None))

def check_origin(request):
    origin=request.headers.get('origin')
    if (origin and origin not in ORIGINS) or request.headers.get('sec-fetch-site') == 'cross-site':
        fail(403,'csrf_rejected')

@dataclass
class Principal:
    user_id: UUID
    membership_id: UUID
    workspace_id: UUID
    session_id: UUID
    email: str
    role: str
    csrf_token: str

def principal(request:Request,token=Depends(cookie_scheme),csrf=Depends(csrf_scheme)):
    if not token or len(token)>256: fail(401,'authentication_required')
    # A separate read transaction keeps import snapshot/locking behavior intact.
    with SessionLocal() as db:
        row=db.execute(select(AuthSession,Membership,User).join(Membership,AuthSession.membership_id==Membership.id).join(User,Membership.user_id==User.id).where(AuthSession.token_hash==digest(token),AuthSession.revoked_at.is_(None),AuthSession.expires_at>utcnow(),Membership.active.is_(True),User.active.is_(True),AuthSession.workspace_id==Membership.workspace_id)).first()
        if not row: fail(401,'authentication_required')
        sess,member,user=row
        p=Principal(user.id,member.id,member.workspace_id,sess.id,user.email,member.role,csrf_for(token))
    if request.method not in ('GET','HEAD','OPTIONS'):
        check_origin(request)
        if not csrf or not hmac.compare_digest(csrf,p.csrf_token): fail(403,'csrf_rejected')
    request.state.auth=p
    return p

def session(p=Depends(principal)): return p.workspace_id
def writer(p=Depends(principal)):
    if p.role not in ('admin','operator'): fail(403,'forbidden')
    return p.workspace_id
def admin(p=Depends(principal)):
    if p.role != 'admin': fail(403,'forbidden')
    return p
def auditor(p=Depends(principal)):
    if p.role not in ('admin','operator'): fail(403,'forbidden')
    return p

def identity(p):
    return dict(id=str(p.user_id),email=p.email,role=p.role,workspace_id=str(p.workspace_id),csrf_token=p.csrf_token)

class Login(BaseModel):
    email: str = Field(min_length=3,max_length=320)
    password: SecretStr = Field(min_length=1,max_length=256)

class CreateUser(Login):
    password: SecretStr = Field(min_length=12,max_length=256)
    role: Literal['admin','operator','viewer']
    @field_validator('role')
    @classmethod
    def valid_role(cls,value):
        if value not in ('admin','operator','viewer'): raise ValueError('invalid role')
        return value
    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        value=value.strip().lower()
        if value.count('@')!=1 or not all(value.split('@')) or any(c.isspace() for c in value): raise ValueError('invalid email')
        return value

class RoleUpdate(BaseModel):
    role: Literal['admin','operator','viewer']
    active: bool = True
    _role = field_validator('role')(CreateUser.valid_role.__func__)

class Identity(BaseModel):
    id: UUID
    email: str
    role: Literal['admin','operator','viewer']
    workspace_id: UUID
    csrf_token: str

class UserView(BaseModel):
    id: UUID
    email: str
    role: Literal['admin','operator','viewer']
    active: bool

class UserPage(BaseModel):
    items: list[UserView]
    total: int
    page: int
    page_size: int

# Bounded per-process IP limiter. No trusting spoofable forwarded headers.
attempts=OrderedDict()
attempt_lock=threading.Lock()
def rate_limit(request):
    key=request.client.host if request.client else 'unknown'
    now=time.monotonic()
    with attempt_lock:
        start,count=attempts.pop(key,(now,0))
        if now-start>=60: start,count=now,0
        attempts[key]=(start,count+1)
        while len(attempts)>1024: attempts.popitem(last=False)
        if count>=10: fail(429,'login_rate_limited')

@router.get('/auth/csrf')
def login_csrf(response:Response):
    nonce=secrets.token_urlsafe(32)
    response.set_cookie(PREAUTH_COOKIE,nonce,httponly=True,secure=SECURE,samesite=SAMESITE,path='/api/v1/auth',max_age=600)
    response.headers['Cache-Control']='no-store'
    return {'csrf_token':nonce}

@router.post('/auth/login',response_model=Identity)
def login(body:Login,request:Request,response:Response,csrf=Depends(csrf_scheme),db=Depends(get_db,scope='function')):
    check_origin(request)
    nonce=request.cookies.get(PREAUTH_COOKIE)
    if not nonce or not csrf or not hmac.compare_digest(nonce,csrf): fail(403,'csrf_rejected')
    rate_limit(request)
    user=db.scalar(select(User).where(User.email==body.email.strip().lower()))
    try: valid=hasher.verify(user.password_hash if user else dummy_hash,body.password.get_secret_value())
    except (VerificationError,InvalidHashError): valid=False
    member=db.scalar(select(Membership).where(Membership.user_id==user.id)) if user else None
    if not valid or not user or not user.active or not member or not member.active:
        audit(db,user.id if user else None,member.workspace_id if member else None,'login.failure','auth')
        db.commit()  # Failure events must survive the HTTP exception rollback.
        fail(401,'invalid_credentials')
    if hasher.check_needs_rehash(user.password_hash): user.password_hash=hasher.hash(body.password.get_secret_value())
    old=request.cookies.get(COOKIE)
    if old:
        previous=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(old)))
        if previous: previous.revoked_at=utcnow()
    token=secrets.token_urlsafe(32)
    sess=AuthSession(membership_id=member.id,workspace_id=member.workspace_id,token_hash=digest(token),expires_at=utcnow()+timedelta(hours=TTL))
    db.add(sess);db.flush()
    audit(db,user.id,member.workspace_id,'login.success','session',sess.id)
    response.set_cookie(COOKIE,token,httponly=True,secure=SECURE,samesite=SAMESITE,path='/',max_age=TTL*3600)
    response.delete_cookie(PREAUTH_COOKIE,path='/api/v1/auth',secure=SECURE,httponly=True,samesite=SAMESITE)
    response.headers['Cache-Control']='no-store'
    return identity(Principal(user.id,member.id,member.workspace_id,sess.id,user.email,member.role,csrf_for(token)))

@router.get('/auth/me',response_model=Identity)
def me(response:Response,p=Depends(principal)):
    response.headers['Cache-Control']='no-store'
    return identity(p)

@router.post('/auth/logout',status_code=204)
def logout(response:Response,p=Depends(principal),db=Depends(get_db,scope='function')):
    db.get(AuthSession,p.session_id).revoked_at=utcnow()
    audit(db,p.user_id,p.workspace_id,'logout','session',p.session_id)
    response.delete_cookie(COOKIE,path='/',secure=SECURE,httponly=True,samesite=SAMESITE)

def user_view(user,member): return dict(id=str(user.id),email=user.email,role=member.role,active=user.active and member.active)

@router.get('/users',tags=['users'],response_model=UserPage)
def users(p=Depends(admin),db=Depends(get_db,scope='function'),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    stmt=select(User,Membership).join(Membership,User.id==Membership.user_id).where(Membership.workspace_id==p.workspace_id)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows=db.execute(stmt.order_by(User.created_at,User.id).offset((page-1)*page_size).limit(page_size))
    return dict(items=[user_view(u,m) for u,m in rows],total=total,page=page,page_size=page_size)

@router.post('/users',status_code=201,tags=['users'],response_model=UserView)
def create_user(body:CreateUser,p=Depends(admin),db=Depends(get_db,scope='function')):
    user=User(email=body.email,password_hash=hasher.hash(body.password.get_secret_value()))
    db.add(user)
    try: db.flush()
    except IntegrityError: fail(409,'user_exists')
    member=Membership(user_id=user.id,workspace_id=p.workspace_id,role=body.role)
    db.add(member);db.flush()
    audit(db,p.user_id,p.workspace_id,'user.created','user',user.id)
    return user_view(user,member)

@router.put('/users/{user_id}/role',tags=['users'],response_model=UserView)
def role_update(user_id:UUID,body:RoleUpdate,p=Depends(admin),db=Depends(get_db,scope='function')):
    db.scalar(select(Workspace).where(Workspace.id==p.workspace_id).with_for_update())
    row=db.execute(select(User,Membership).join(Membership,User.id==Membership.user_id).where(User.id==user_id,Membership.workspace_id==p.workspace_id).with_for_update()).first()
    if not row: fail(404,'user_not_found')
    user,member=row
    if member.role=='admin' and member.active and user.active and (body.role!='admin' or not body.active):
        count=db.scalar(select(func.count()).select_from(Membership).join(User).where(Membership.workspace_id==p.workspace_id,Membership.role=='admin',Membership.active.is_(True),User.active.is_(True)))
        if count<=1: fail(409,'last_admin')
    member.role=body.role;member.active=body.active
    for sess in db.scalars(select(AuthSession).where(AuthSession.membership_id==member.id,AuthSession.revoked_at.is_(None))): sess.revoked_at=utcnow()
    audit(db,p.user_id,p.workspace_id,'user.role_changed','user',user.id)
    return user_view(user,member)

@router.get('/audit-logs',tags=['audit'])
def audit_logs(p=Depends(auditor),db=Depends(get_db,scope='function'),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    stmt=select(AuditLog).where(AuditLog.workspace_id==p.workspace_id)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows=db.scalars(stmt.order_by(AuditLog.created_at.desc(),AuditLog.id.desc()).offset((page-1)*page_size).limit(page_size))
    return dict(items=[dict(id=str(r.id),actor=str(r.actor_id) if r.actor_id else None,workspace_id=str(r.workspace_id),action=r.action,entity=r.entity,entity_id=r.entity_id,timestamp=r.created_at.isoformat()) for r in rows],total=total,page=page,page_size=page_size)

@router.get('/api-keys',tags=['contracts'])
def api_keys(p=Depends(admin)): return {'implemented':False,'items':[]}


