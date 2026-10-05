from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID
from typing import Literal
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, Request
from fastapi.responses import Response
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session
from . import schemas as s
from .database import get_db, engine
from .models import Workspace, Import, ImportRow, ValidationIssue, Lead, IntegrationConfig
from .persistence import workspace, item_for, activity, serialize, analyze_item, commit_item, row_list
from .imports import FIELDS, parse_csv, safe_csv

from .config import VERSION, production, demo_mode
from .request_limit import UploadBodyLimit
from .observability import log
from uuid import uuid4
import time
app = FastAPI(title='AstraSynq API',version=VERSION,docs_url=None if production() else '/docs',redoc_url=None if production() else '/redoc',openapi_url=None if production() else '/openapi.json',description='Server sessions and workspace RBAC. Login requires /auth/csrf and X-CSRF-Token; mutations require the token returned by login/me.')
app.add_middleware(UploadBodyLimit)
from .auth import router, session, writer, admin, audit
app.include_router(router)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Never echo password/request input in validation responses.
    return JSONResponse(status_code=422,content={'detail':{'code':'invalid_input'}})

@app.middleware('http')
async def security_headers(request, call_next):
    request_id=str(uuid4()); request.state.request_id=request_id; started=time.monotonic()
    try:
        if demo_mode() and (request.url.path.startswith('/api/') or request.url.path=='/health/ready'):
            from starlette.concurrency import run_in_threadpool
            from .database import SessionLocal
            from .demo import reserve_request
            import re
            path=request.url.path
            allowed = request.method in ('GET','HEAD') or (
                request.method == 'POST' and (path in ('/api/v1/auth/login','/api/v1/auth/logout','/api/v1/imports') or
                re.fullmatch(r'/api/v1/imports/[0-9a-f-]{36}/(analyze|commit)',path))) or (
                request.method == 'PUT' and re.fullmatch(r'/api/v1/imports/[0-9a-f-]{36}/mapping',path))
            if not allowed:
                raise HTTPException(403, {'code':'demo_operation_disabled'})
            def budget():
                with SessionLocal.begin() as db: reserve_request(db)
            await run_in_threadpool(budget)
        response=await call_next(request)
    except HTTPException as exc:
        response=JSONResponse(status_code=exc.status_code,content={'detail':exc.detail})
    except Exception:
        log('request.failed', request_id=request_id, method=request.method)
        response=JSONResponse(status_code=500, content={'detail':{'code':'api_unavailable'}})
    response.headers['X-Request-ID']=request_id
    response.headers['Content-Security-Policy']="default-src 'none'; frame-ancestors 'none'; base-uri 'none'" if production() or request.url.path not in ('/docs','/redoc') else "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
    response.headers['X-Frame-Options']='DENY'
    if demo_mode():
        response.headers['X-AstraSynq-Mode']='synthetic-demo'
        if production(): response.headers['Strict-Transport-Security']='max-age=31536000'
        if response.headers.get('content-type','').startswith('text/html') or (request.url.path=='/' and response.status_code==304):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    if production() and request.url.scheme=='https':
        response.headers['Strict-Transport-Security']='max-age=31536000'
    log('request.completed', request_id=request_id, method=request.method, status=response.status_code, duration_ms=round((time.monotonic()-started)*1000))
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Frame-Options']='DENY'
    return response
errors = {422:{'model':s.ErrorResponse},404:{'model':s.ErrorResponse},409:{'model':s.ErrorResponse}}

@app.get('/health/live',response_model=s.Health,tags=['health'])
def live(): return s.Health(status='ok')

@app.get('/health/ready',response_model=s.Health,responses={503:{'model':s.Health}},tags=['health'])
def ready():
    try:
        with engine.connect() as conn:
            revision = conn.execute(text('SELECT version_num FROM alembic_version')).scalar()
            if revision != 'a5release00001': raise RuntimeError('migrations required')
    except Exception:
        return Response(s.Health(status='not_ready').model_dump_json(),status_code=503,media_type='application/json')
    return s.Health(status='ready')

@app.get('/api/v1/dashboard/summary',response_model=s.Summary,tags=['dashboard'])
def summary(key=Depends(session),db:Session=Depends(get_db,scope="function")):
    db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
    records = db.scalar(select(func.count()).select_from(Lead).where(Lead.workspace_id == key))
    counts = db.execute(select(func.count(),func.coalesce(func.sum(Import.valid),0),func.coalesce(func.sum(Import.invalid),0),func.coalesce(func.sum(Import.duplicate),0)).where(Import.workspace_id == key,Import.status == 'completed')).one()
    imports = list(db.scalars(select(Import).where(Import.workspace_id == key,Import.status == 'completed').order_by(Import.created_at.desc(),Import.id.desc()).limit(20)))
    latest = list(db.scalars(select(Lead).where(Lead.workspace_id == key).order_by(Lead.created_at.desc(),Lead.id.desc()).limit(10)))
    now=datetime.now(timezone.utc)
    start=(now-timedelta(days=13)).replace(hour=0,minute=0,second=0,microsecond=0)
    daily=dict(db.execute(select(func.date(Lead.created_at),func.count()).where(Lead.workspace_id == key,Lead.created_at >= start).group_by(func.date(Lead.created_at))).all())
    series=[dict(date=(start+timedelta(days=i)).date().isoformat(),label=(start+timedelta(days=i)).strftime('%b %d'),records=daily.get((start+timedelta(days=i)).date(),0)) for i in range(14)]
    count,valid,invalid,duplicate=counts
    return dict(integration_count=db.scalar(select(func.count()).select_from(IntegrationConfig).where(IntegrationConfig.workspace_id==key,IntegrationConfig.enabled.is_(True))),record_count=records,import_count=count,valid=valid,invalid=invalid,duplicate=duplicate,
        quality=round(valid/max(1,valid+invalid+duplicate)*100,1),series=series,
        imports=[activity(i) for i in imports],records=[r.data for r in latest])

@app.get('/api/v1/samples/leads.csv',tags=['samples'])
def sample():
    if demo_mode():
        from .demo import SAMPLE
        return Response(SAMPLE.read_bytes(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="synthetic-demo.csv"'})
    return Response((Path(__file__).parents[1]/'samples'/'leads.csv').read_text(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="astrasynq_sample.csv"'})

@app.post('/api/v1/imports',response_model=s.ImportResult,status_code=201,responses=errors,tags=['imports'])
async def upload(file:UploadFile=File(...),key=Depends(writer),db:Session=Depends(get_db,scope="function")):
    try:
        if not (file.filename or '').lower().endswith('.csv'): raise HTTPException(422,{'code':'csv_extension'})
        if file.content_type not in ('text/csv','application/csv','text/plain','application/octet-stream',None): raise HTTPException(422,{'code':'csv_extension'})
        content=await file.read(5*1024*1024+1)
    finally:
        await file.close()
    if len(content)>5*1024*1024: raise HTTPException(413,{'code':'file_limit'})
    if demo_mode():
        from .demo import accept_sample
        accept_sample(content)
    columns,raw=parse_csv(content)
    fields={field:next((c for c in columns if c.lower().strip()==field),'') for field in FIELDS}
    workspace(db,key)
    if demo_mode():
        from .demo import MAX_IMPORTS
        if db.scalar(select(func.count()).select_from(Import).where(Import.workspace_id==key)) >= MAX_IMPORTS:
            raise HTTPException(429,{'code':'demo_import_limit'})
    item=Import(workspace_id=key,filename=Path(file.filename).name[:120],columns=columns,mapping={k:v for k,v in fields.items() if v},total=len(raw))
    if demo_mode(): item.filename='synthetic-demo.csv'
    db.add(item);db.flush()
    db.add_all([ImportRow(import_id=item.id,row_number=n,raw=r) for n,r in enumerate(raw,2)])
    db.flush()
    return serialize(db,item)

@app.get('/api/v1/imports',response_model=s.ImportPage,tags=['imports'])
def list_imports(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),
    status:Literal['uploaded','mapped','analyzed','completed']|None=None,search:str=Query('',max_length=120),
    key=Depends(session),db:Session=Depends(get_db,scope="function")):
    db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
    stmt=select(Import).where(Import.workspace_id == key)
    if status: stmt=stmt.where(Import.status == status)
    if search: stmt=stmt.where(Import.filename.ilike('%'+search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    items=db.scalars(stmt.order_by(Import.created_at.desc(),Import.id.desc()).offset((page-1)*page_size).limit(page_size))
    return dict(items=[activity(i) for i in items],total=total,page=page,page_size=page_size)

@app.get('/api/v1/imports/{import_id}',response_model=s.ImportResult,responses=errors,tags=['imports'])
def get_import(import_id:str,key=Depends(session),db:Session=Depends(get_db,scope="function")):
    db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
    return serialize(db,item_for(db,key,import_id))

@app.put('/api/v1/imports/{import_id}/mapping',response_model=s.ImportResult,responses=errors,tags=['imports'])
def mapping(import_id:str,body:s.Mapping,key=Depends(writer),db:Session=Depends(get_db,scope="function")):
    workspace(db,key);item=item_for(db,key,import_id,True)
    if item.status=='completed': raise HTTPException(409,{'code':'remap_completed'})
    if 'email' not in body.fields or any(f not in FIELDS or c not in item.columns for f,c in body.fields.items()) or len(set(body.fields.values()))!=len(body.fields):
        raise HTTPException(422,{'code':'invalid_mapping'})
    db.execute(delete(ValidationIssue).where(ValidationIssue.row_id.in_(select(ImportRow.id).where(ImportRow.import_id == item.id))))
    for row in row_list(db,item): row.data={};row.classification=None
    item.mapping=body.fields;item.status='mapped';item.valid=item.invalid=item.duplicate=0
    db.flush();return serialize(db,item)

@app.post('/api/v1/imports/{import_id}/analyze',response_model=s.ImportResult,responses=errors,tags=['imports'])
def analyze(import_id:str,request:Request,key=Depends(writer),db:Session=Depends(get_db,scope="function")):
    workspace(db,key);item=item_for(db,key,import_id,True)
    if item.status=='completed': raise HTTPException(409,{'code':'reanalyze_completed'})
    analyze_item(db,item);audit(db,request.state.auth.user_id,key,'import.analyzed','import',item.id);return serialize(db,item)

@app.post('/api/v1/imports/{import_id}/commit',response_model=s.CommitResult,responses=errors,tags=['imports'])
def commit(import_id:str,request:Request,key=Depends(writer),db:Session=Depends(get_db,scope="function")):
    workspace(db,key);item=item_for(db,key,import_id,True);result=commit_item(db,item)
    if demo_mode():
        from .demo import complete_mock
        complete_mock(db,key)
    audit(db,request.state.auth.user_id,key,'import.committed','import',item.id);return result

@app.get('/api/v1/imports/{import_id}/issues.csv',tags=['imports'])
def issues(import_id:str,request:Request,key=Depends(session),db:Session=Depends(get_db,scope="function")):
    item=item_for(db,key,import_id)
    if item.status not in ['analyzed','completed']: raise HTTPException(409,{'code':'report_first'})
    rows=[['row','classification','email','field','code']]
    for row in serialize(db,item)['rows']:
        for issue in row['issues']: rows.append([row['row_number'],row['classification'],row['data'].get('email',''),issue['field'],issue['code']])
    audit(db,request.state.auth.user_id,key,'export','import',item.id)
    return Response(safe_csv(rows),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="issues.csv"'})

def lead_query(key,search='',company='',import_id=None):
    stmt=select(Lead).where(Lead.workspace_id == key)
    if search:
        pattern='%'+search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        stmt=stmt.where(Lead.email_normalized.ilike(pattern,escape='\\') | Lead.data['name'].astext.ilike(pattern,escape='\\'))
    if company: stmt=stmt.where(Lead.data['company'].astext == company)
    if import_id: stmt=stmt.where(Lead.import_id == import_id)
    return stmt

@app.get('/api/v1/leads/export.csv',tags=['leads'])
def export(request:Request,search:str=Query('',max_length=120),company:str=Query('',max_length=120),import_id:UUID|None=None,key=Depends(session),db:Session=Depends(get_db,scope="function")):
    records=db.scalars(lead_query(key,search,company,import_id).order_by(Lead.created_at.desc(),Lead.id.desc()))
    rows=[FIELDS]+[[r.data.get(field,'') for field in FIELDS] for r in records]
    audit(db,request.state.auth.user_id,key,'export','leads')
    return Response(safe_csv(rows),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="leads.csv"'})

@app.get('/api/v1/leads',response_model=s.LeadPage,tags=['leads'])
def list_leads(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),search:str=Query('',max_length=120),company:str=Query('',max_length=120),import_id:UUID|None=None,key=Depends(session),db:Session=Depends(get_db,scope="function")):
    db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
    stmt=lead_query(key,search,company,import_id)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows=db.scalars(stmt.order_by(Lead.created_at.desc(),Lead.id.desc()).offset((page-1)*page_size).limit(page_size))
    return dict(items=[dict(id=str(r.id),import_id=str(r.import_id),email_normalized=r.email_normalized,created_at=r.created_at.isoformat(),data=r.data) for r in rows],total=total,page=page,page_size=page_size)


from .integrations import router as integration_router
app.include_router(integration_router)

# Same-origin serving is demo-only. Normal API/frontend/worker topology is unchanged.
if demo_mode():
    import os
    from starlette.staticfiles import StaticFiles
    static_dir=os.getenv('ASTRASYNQ_DEMO_STATIC_DIR','')
    if static_dir:
        app.mount('/',StaticFiles(directory=static_dir,html=True),name='synthetic-demo-ui')



