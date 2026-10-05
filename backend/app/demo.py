"""Explicit synthetic sandbox. No public reset, no network transport, no daemon."""
from datetime import timedelta
from pathlib import Path
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func, text, delete
from .models import (Workspace, User, Membership, Import, ImportRow, Lead,
                     IntegrationConfig, Delivery, Job, Event, AuditLog, utcnow)

SCOPE = UUID('00000000-0000-4000-8000-000000000042')
EMAIL = 'demo@example.test'
SAMPLE = Path(__file__).parents[1] / 'samples' / 'demo.csv'
MAX_IMPORTS = 30

def require_scope(scope):
    if scope != SCOPE:
        raise HTTPException(403, {'code': 'demo_scope_required'})

def accept_sample(content):
    # Exact bytes: do not persist arbitrary input, filenames, extra columns or PII.
    if content != SAMPLE.read_bytes():
        raise HTTPException(422, {'code': 'demo_sample_only'})

def reserve_request(db):
    """Shared, durable aggregate budget; no IP/headers/PII saved. Fail closed."""
    if not db.scalar(text('SELECT pg_try_advisory_xact_lock(504205042)')):
        raise HTTPException(429, {'code': 'demo_busy'})
    now = utcnow()
    # Prune only our anonymous budget rows, never user audit events.
    db.execute(delete(AuditLog).where(AuditLog.action == 'demo.request', AuditLog.created_at < now-timedelta(days=1)))
    stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action == 'demo.request')
    if db.scalar(stmt) >= 2000 or db.scalar(stmt.where(AuditLog.created_at >= now-timedelta(minutes=1))) >= 120:
        raise HTTPException(429, {'code': 'demo_rate_limited'})
    db.add(AuditLog(action='demo.request', entity='sandbox'))

def complete_mock(db, scope):
    require_scope(scope)
    rows = db.execute(select(Job, Delivery).join(Delivery, Job.delivery_id == Delivery.id)
        .where(Delivery.workspace_id == scope, Job.status == 'queued')
        .with_for_update(of=Job).limit(10)).all()
    for job, delivery in rows:
        job.status='completed'; job.attempts=1
        delivery.status='delivered'; delivery.attempts=1; delivery.response_code=None
        delivery.last_error='synthetic_sink'; delivery.delivered_at=delivery.updated_at=utcnow()
        db.add(AuditLog(workspace_id=scope, action='demo.delivery.simulated', entity='delivery', entity_id=str(delivery.id)))
    return len(rows)

def seed(db, password, reset=False):
    from .config import demo_mode
    from .auth import hasher
    from .imports import parse_csv, FIELDS
    from .persistence import analyze_item, commit_item
    if not demo_mode():
        raise RuntimeError('Synthetic seed/reset requires demo mode')
    if not 24 <= len(password) <= 256:
        raise RuntimeError('Generated demo password required')
    db.execute(text('SELECT pg_advisory_xact_lock(504205043)'))
    scopes=list(db.scalars(select(Workspace.id)))
    if any(s != SCOPE for s in scopes) or db.scalar(select(User.id).where(User.email != EMAIL).limit(1)):
        raise RuntimeError('Seed/reset requires a dedicated synthetic database')
    existing=db.get(Workspace,SCOPE)
    if reset and existing:
        # Delete restrictive lead references first; then scoped FK cascades.
        db.execute(delete(Lead).where(Lead.workspace_id == SCOPE))
        db.delete(existing); db.flush()
        db.execute(delete(User).where(User.email == EMAIL)); db.flush()
        existing=None
    if existing:
        member=db.scalar(select(Membership).where(Membership.workspace_id == SCOPE))
        if not member or member.role != 'operator':
            raise RuntimeError('Unexpected demo membership')
        user=db.get(User,member.user_id)
        if not hasher.verify(user.password_hash,password):
            raise RuntimeError('Use explicit offline reset to rotate the demo password')
        return False
    db.add(Workspace(id=SCOPE)); db.flush()
    user=User(email=EMAIL,password_hash=hasher.hash(password)); db.add(user); db.flush()
    db.add(Membership(user_id=user.id,workspace_id=SCOPE,role='operator'))
    db.add(IntegrationConfig(workspace_id=SCOPE,kind='webhook',enabled=True,destination='synthetic://sink',credential_ref=''))
    db.flush()
    baseline=SAMPLE.read_bytes().replace(b'synthetic01@',b'baseline01@').replace(b'synthetic02@',b'baseline02@')
    columns,raw=parse_csv(baseline)
    item=Import(workspace_id=SCOPE,filename='synthetic-demo.csv',columns=columns,mapping={k:k for k in FIELDS if k in columns},total=len(raw))
    db.add(item); db.flush()
    db.add_all([ImportRow(import_id=item.id,row_number=n,raw=r) for n,r in enumerate(raw,2)])
    db.flush(); analyze_item(db,item); commit_item(db,item); complete_mock(db,SCOPE)
    return True

def main():
    import argparse, os
    from .database import SessionLocal
    parser=argparse.ArgumentParser(); parser.add_argument('--reset',action='store_true'); args=parser.parse_args()
    with SessionLocal.begin() as db:
        seed(db,os.getenv('ASTRASYNQ_DEMO_PASSWORD',''),reset=args.reset)
    print('Synthetic sandbox ready; credentials are never printed.')

if __name__ == '__main__': main()
