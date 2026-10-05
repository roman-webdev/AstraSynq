from uuid import uuid4
from datetime import timedelta
import secrets
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Workspace, User, Membership, AuthSession, utcnow
from app.auth import hasher, digest, csrf_for

# Regression fixtures create authentic persisted sessions, never override auth dependencies.
def credentials(role='admin',scope=None,seed_data=False):
    key=scope or uuid4();token=secrets.token_urlsafe(32)
    with SessionLocal.begin() as db:
        if not db.get(Workspace,key): db.add(Workspace(id=key));db.flush()
        if seed_data:
            from app.store import seed
            seed(db,key)
        u=User(email=f'{uuid4()}@example.test',password_hash=hasher.hash('Fixture only password 123!'))
        db.add(u);db.flush();m=Membership(user_id=u.id,workspace_id=key,role=role);db.add(m);db.flush()
        db.add(AuthSession(membership_id=m.id,workspace_id=key,token_hash=digest(token),expires_at=utcnow()+timedelta(hours=1)))
    return {'Cookie':f'astrasynq_session={token}','X-CSRF-Token':csrf_for(token)}
