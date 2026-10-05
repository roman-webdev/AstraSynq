"""Transactional import lifecycle. PostgreSQL locks protect cross-process writes."""
from uuid import UUID
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from fastapi import HTTPException
from .models import Workspace, Import, ImportRow, ValidationIssue, Lead, utcnow
from .imports import classify

def workspace(db, key):
    db.execute(insert(Workspace).values(id=key).on_conflict_do_nothing())
    # One writer per workspace; unlike a Python lock this works across API processes.
    db.execute(select(Workspace).where(Workspace.id == key).with_for_update()).scalar_one()

def item_for(db, key, import_id, lock=False):
    try: ident = UUID(import_id)
    except ValueError: raise HTTPException(404, {'code':'import_missing'})
    stmt = select(Import).where(Import.id == ident, Import.workspace_id == key)
    if lock: stmt = stmt.with_for_update()
    item = db.scalar(stmt)
    if item is None: raise HTTPException(404, {'code':'import_missing'})
    return item

def row_list(db, item):
    return list(db.scalars(select(ImportRow).where(ImportRow.import_id == item.id).order_by(ImportRow.row_number)))

def activity(item):
    return {**{k:getattr(item,k) for k in ['filename','status','total','valid','invalid','duplicate']},
            'id':str(item.id), 'created_at':item.created_at.isoformat()}

def serialize(db, item):
    rows = row_list(db,item)
    issues = {}
    for issue in db.scalars(select(ValidationIssue).join(ImportRow, ValidationIssue.row_id == ImportRow.id).where(ImportRow.import_id == item.id)):
        issues.setdefault(issue.row_id,[]).append({'field':issue.field,'code':issue.code})
    return {**activity(item), 'columns':item.columns, 'mapping':item.mapping, 'inserted':item.inserted,
        'rows':[dict(row_number=r.row_number,data=r.data,classification=r.classification,
            issues=sorted(issues.get(r.id,[]),key=lambda x:(x['field'],x['code']))) for r in rows if r.classification]}

def analyze_item(db, item):
    if 'email' not in item.mapping: raise HTTPException(422, {'code':'map_email'})
    rows = row_list(db,item)
    emails = {r.raw.get(item.mapping['email'],'').strip().lower() for r in rows}
    existing = set(db.scalars(select(Lead.email_normalized).where(Lead.email_normalized.in_(emails))))
    results = classify([r.raw for r in rows], item.mapping, existing)
    db.execute(delete(ValidationIssue).where(ValidationIssue.row_id.in_(select(ImportRow.id).where(ImportRow.import_id == item.id))))
    for row, result in zip(rows,results):
        row.data = result['data']; row.classification = result['classification']
        for issue in result['issues']: db.add(ValidationIssue(row_id=row.id, **issue))
    for category in ['valid','invalid','duplicate']:
        setattr(item,category,sum(r['classification'] == category for r in results))
    item.status = 'analyzed'; item.updated_at = utcnow()
    db.flush()
    return rows

def commit_item(db, item):
    if item.status == 'completed': return {'import_id':str(item.id),'inserted':item.inserted}
    if item.status != 'analyzed': raise HTTPException(409, {'code':'analyze_first'})
    previous = item.valid
    rows = analyze_item(db,item)
    if previous != item.valid:
        # Persist refreshed review before the client receives the conflict.
        db.commit()
        raise HTTPException(409, {'code':'workspace_changed'})
    # Savepoint makes the entire insertion attempt atomic if another workspace
    # concurrently inserts a globally unique email after our analysis snapshot.
    collision = False
    with db.begin_nested() as attempt:
        for row in rows:
            if row.classification != 'valid': continue
            data = dict(row.data)
            if not data.get('created_at'): data['created_at'] = utcnow().isoformat()
            result = db.execute(insert(Lead).values(workspace_id=item.workspace_id, import_id=item.id,
                source_row_id=row.id,email_normalized=data['email'],data=data)
                .on_conflict_do_nothing(index_elements=['email_normalized']).returning(Lead.id)).scalar()
            if result is None:
                collision = True
                break
        if collision: attempt.rollback()
    if collision:
        analyze_item(db,item); db.commit()
        raise HTTPException(409, {'code':'workspace_changed'})
    item.inserted = item.valid; item.status = 'completed'; item.committed_at = utcnow()
    from .automation import emit
    emit(db,item.workspace_id,'import.completed',f'import:{item.id}',dict(import_id=str(item.id),status='completed',total=item.total,inserted=item.inserted,invalid=item.invalid,duplicate=item.duplicate))
    db.flush()
    return {'import_id':str(item.id),'inserted':item.inserted}

