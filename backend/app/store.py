"""Explicit, idempotent PostgreSQL demo seed; no runtime in-memory store."""
from datetime import timedelta
from uuid import UUID
from sqlalchemy import select
from .database import SessionLocal
from .models import Import, ImportRow, Lead, ValidationIssue, utcnow
from .persistence import workspace
DEMO_WORKSPACE = UUID('00000000-0000-4000-8000-000000000001')

def seed(db, key=DEMO_WORKSPACE):
    workspace(db,key)
    if db.scalar(select(Import.id).where(Import.workspace_id == key).limit(1)): return False
    now=utcnow()
    names=['website_leads.csv','crm_contacts.csv','campaign_export.csv','partner_leads.csv','newsletter.csv','sales_pipeline.csv']
    for batch in range(6):
        stamp=now-timedelta(days=batch+1)
        item=Import(workspace_id=key,filename=names[batch],status='completed',columns=['email','name','company','amount','currency'],mapping={k:k for k in ['email','name','company','amount','currency']},total=45,valid=40,invalid=3,duplicate=2,inserted=40,created_at=stamp,committed_at=stamp)
        db.add(item);db.flush()
        for n in range(45):
            i=batch*40+min(n,39)
            data=dict(email='alex@example.com' if i==0 else f'person{i}@example.com',name=f'Sample lead {i+1}',company=['Northstar','Orbit Studio','Acme'][i%3],amount=str(250+i*15),currency='USD',created_at=stamp.isoformat())
            kind='valid' if n<40 else 'invalid' if n<43 else 'duplicate'
            if kind=='invalid': data['email']='invalid-email'
            row=ImportRow(import_id=item.id,row_number=n+2,raw=data,data=data,classification=kind,created_at=stamp)
            db.add(row);db.flush()
            if kind=='valid': db.add(Lead(workspace_id=key,import_id=item.id,source_row_id=row.id,email_normalized=data['email'],data=data,created_at=stamp))
            else: db.add(ValidationIssue(row_id=row.id,field='email',code='invalid_email' if kind=='invalid' else 'duplicate_record',created_at=stamp))
    db.flush();return True

if __name__ == '__main__':
    with SessionLocal.begin() as db: print('Demo seeded' if seed(db) else 'Demo already exists; unchanged')
