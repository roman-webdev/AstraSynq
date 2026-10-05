"""Isolated browser QA database only. Secrets returned to parent pipe, never logged."""
import json
import secrets
from uuid import uuid4
from sqlalchemy import text
from app.database import SessionLocal,engine,DATABASE_URL
from app.models import User,Membership
from app.auth import hasher
from app.store import seed,DEMO_WORKSPACE
if not DATABASE_URL.endswith('/astrasynq_test'): raise SystemExit('Browser QA requires astrasynq_test')
password=secrets.token_urlsafe(32)
with engine.begin() as conn: conn.execute(text('TRUNCATE users,workspaces CASCADE'))
with SessionLocal.begin() as db:
    seed(db)
    for role in ['admin','operator','viewer']:
        user=User(email=f'qa-{role}@example.test',password_hash=hasher.hash(password));db.add(user);db.flush()
        db.add(Membership(user_id=user.id,workspace_id=DEMO_WORKSPACE,role=role))
print(json.dumps({'password':password}))
