"""Explicit local bootstrap; password from hidden prompt or temporary environment."""
import getpass
import os
from uuid import UUID
from sqlalchemy import select
from pydantic import ValidationError
from .database import SessionLocal
from .models import Workspace, User, Membership
from .auth import CreateUser, hasher, audit

def main():
    email=os.getenv('ASTRASYNQ_ADMIN_EMAIL') or input('Admin email: ').strip()
    password=os.getenv('ASTRASYNQ_ADMIN_PASSWORD') or getpass.getpass('Admin password (12+ characters): ')
    try: body=CreateUser(email=email,password=password,role='admin')
    except ValidationError: raise SystemExit('Invalid email/password. Password must be 12..256 characters.') from None
    with SessionLocal.begin() as db:
        scopes=list(db.scalars(select(Workspace.id)))
        supplied=os.getenv('ASTRASYNQ_WORKSPACE_ID')
        scope=UUID(supplied) if supplied else scopes[0] if len(scopes)==1 else None
        if scope not in scopes: raise SystemExit('Set ASTRASYNQ_WORKSPACE_ID to an existing workspace UUID (see DB); bootstrap never creates a workspace.')
        db.scalar(select(Workspace).where(Workspace.id==scope).with_for_update())
        existing=db.scalar(select(Membership.id).join(User).where(Membership.workspace_id==scope,Membership.role=='admin',Membership.active.is_(True),User.active.is_(True)))
        if existing: raise SystemExit('Active Admin already exists; use Admin Users screen. Bootstrap makes no changes.')
        if db.scalar(select(User.id).where(User.email==body.email)): raise SystemExit('User exists; bootstrap makes no changes.')
        user=User(email=body.email,password_hash=hasher.hash(body.password.get_secret_value()))
        db.add(user);db.flush()
        db.add(Membership(user_id=user.id,workspace_id=scope,role='admin'))
        audit(db,user.id,scope,'user.created','user',user.id)
    print('Admin created. Sign in using the supplied email and password.')

if __name__=='__main__': main()
