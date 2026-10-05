from datetime import datetime
"""Workspace-scoped integration configuration, delivery history and schedules."""
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from .database import get_db
from .auth import session, admin, principal, writer, audit
from .models import IntegrationConfig, Delivery, Event, Job, Schedule, WorkerHeartbeat, utcnow
from datetime import timedelta
from .automation import emit, validate_ref, resolve_url, next_daily
router=APIRouter(prefix='/api/v1',tags=['automation'])
Kind=Literal['webhook','telegram']

class ConfigBody(BaseModel):
    enabled: bool=False
    destination: str=Field(max_length=2048)
    credential_ref: str=Field(max_length=128)
    timeout: int=Field(default=10,ge=1,le=20)
    max_attempts: int=Field(default=5,ge=1,le=10)
    backoff: int=Field(default=30,ge=1,le=3600)

class ScheduleBody(BaseModel):
    enabled: bool=False
    timezone: str=Field(default='UTC',max_length=64)



class ConfigView(BaseModel):
    id: UUID
    kind: Kind
    enabled: bool
    destination: str
    credential_ref: str
    credential_mask: str
    timeout: int
    max_attempts: int
    backoff: int
    updated_at: datetime

class IntegrationPage(BaseModel):
    implemented: bool
    items: list[ConfigView]
    can_manage: bool

class ScheduleView(BaseModel):
    enabled: bool
    timezone: str
    next_run_at: datetime | None
    hour: int

class DeliveryView(BaseModel):
    id: UUID
    event_id: UUID
    event_type: str
    integration: Kind
    status: str
    attempts: int
    last_response: str | None
    response_code: int | None
    next_retry: datetime | None
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None
    can_retry: bool

class DeliveryPage(BaseModel):
    total: int
    items: list[DeliveryView]


def view(c):
    return dict(id=str(c.id),kind=c.kind,enabled=c.enabled,destination=c.destination,credential_ref=c.credential_ref,credential_mask='••••••••' if c.credential_ref else '',timeout=c.timeout,max_attempts=c.max_attempts,backoff=c.backoff,updated_at=c.updated_at)

def config(db,key,kind,lock=False):
    stmt=select(IntegrationConfig).where(IntegrationConfig.workspace_id==key,IntegrationConfig.kind==kind)
    if lock: stmt=stmt.with_for_update()
    c=db.scalar(stmt)
    if not c: raise HTTPException(404,{'code':'integration_missing'})
    return c

@router.get('/integrations',response_model=IntegrationPage)
def integrations(p=Depends(principal),db=Depends(get_db,scope='function')):
    return dict(implemented=True,items=[view(c) for c in db.scalars(select(IntegrationConfig).where(IntegrationConfig.workspace_id==p.workspace_id))],can_manage=p.role=='admin')

@router.put('/integrations/{kind}',response_model=ConfigView)
def configure(kind:Kind,body:ConfigBody,p=Depends(admin),db=Depends(get_db,scope='function')):
    try:
        validate_ref(body.credential_ref)
        if kind=='webhook': resolve_url(body.destination)
        else:
            import re
            if not re.fullmatch(r'-?[0-9]{1,20}',body.destination): raise ValueError('chat_id_invalid')
    except (ValueError,OSError): raise HTTPException(422,{'code':'integration_config_invalid'})
    # Serialize initial config creation and edits with import recipient snapshots.
    from .persistence import workspace
    workspace(db,p.workspace_id)
    c=db.scalar(select(IntegrationConfig).where(IntegrationConfig.workspace_id==p.workspace_id,IntegrationConfig.kind==kind).with_for_update())
    if not c: c=IntegrationConfig(workspace_id=p.workspace_id,kind=kind);db.add(c)
    for name,value in body.model_dump().items(): setattr(c,name,value)
    db.flush();audit(db,p.user_id,p.workspace_id,'integration.changed','integration',c.id)
    return view(c)

@router.post('/integrations/{kind}/test',status_code=202)
def test(kind:Kind,p=Depends(principal),db=Depends(get_db,scope='function')):
    if p.role not in ('admin','operator'): raise HTTPException(403,{'code':'forbidden'})
    c=config(db,p.workspace_id,kind,True)
    # Rate bound per integration; test works while disabled, using saved destination only.
    if db.scalar(select(func.count()).select_from(Delivery).where(Delivery.integration_id==c.id,Delivery.status.in_(['queued','running','retry'])))>=10:
        raise HTTPException(409,{'code':'delivery_busy'})
    event_id=emit(db,p.workspace_id,'integration.test',f'test:{uuid4()}',dict(status='test',total=0,inserted=0),[c])
    audit(db,p.user_id,p.workspace_id,'delivery.test','event',event_id)
    return dict(event_id=str(event_id),status='queued')

@router.get('/deliveries',response_model=DeliveryPage)
def deliveries(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),key=Depends(session),db=Depends(get_db,scope='function')):
    stmt=select(Delivery,Event,IntegrationConfig,Job).join(Event,Delivery.event_id==Event.id).join(IntegrationConfig,Delivery.integration_id==IntegrationConfig.id).join(Job,Job.delivery_id==Delivery.id).where(Delivery.workspace_id==key)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows=db.execute(stmt.order_by(Delivery.created_at.desc(),Delivery.id.desc()).offset((page-1)*page_size).limit(page_size))
    return dict(total=total,items=[dict(id=str(d.id),event_id=str(e.id),event_type=e.type,integration=c.kind,status=d.status,attempts=d.attempts,last_response=d.last_error,response_code=d.response_code,next_retry=j.run_after if j.status=='retry' else None,created_at=d.created_at,updated_at=d.updated_at,delivered_at=d.delivered_at,can_retry=d.status in ('failed','paused') and c.enabled) for d,e,c,j in rows])

@router.post('/deliveries/{delivery_id}/retry',status_code=202)
def retry(delivery_id:UUID,p=Depends(principal),db=Depends(get_db,scope='function')):
    if p.role not in ('admin','operator'): raise HTTPException(403,{'code':'forbidden'})
    j=db.scalar(select(Job).join(Delivery,Job.delivery_id==Delivery.id).where(Delivery.id==delivery_id,Delivery.workspace_id==p.workspace_id).with_for_update(of=Job))
    if not j: raise HTTPException(404,{'code':'delivery_missing'})
    d=db.get(Delivery,delivery_id);c=db.get(IntegrationConfig,d.integration_id)
    if j.status not in ('failed','paused') or not c.enabled: raise HTTPException(409,{'code':'retry_not_allowed'})
    j.status='queued';j.attempts=0;j.max_attempts=c.max_attempts;j.backoff=c.backoff;j.run_after=utcnow();j.lease_until=None;j.lease_token=None
    d.status='queued';d.updated_at=utcnow()
    # Lifetime delivery attempts remain intact. Per-retry job budget starts afresh.
    audit(db,p.user_id,p.workspace_id,'delivery.retry','delivery',d.id)
    return dict(id=str(d.id),status=d.status)

@router.get('/automations',response_model=ScheduleView)
def schedules(key=Depends(session),db=Depends(get_db,scope='function')):
    s=db.scalar(select(Schedule).where(Schedule.workspace_id==key))
    return dict(enabled=s.enabled if s else False,timezone=s.timezone if s else 'UTC',next_run_at=s.next_run_at if s else None,hour=9)

@router.put('/automations/daily-summary',response_model=ScheduleView)
def schedule(body:ScheduleBody,p=Depends(admin),db=Depends(get_db,scope='function')):
    try: ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError,ValueError): raise HTTPException(422,{'code':'timezone_invalid'})
    from .persistence import workspace
    workspace(db,p.workspace_id)
    s=db.scalar(select(Schedule).where(Schedule.workspace_id==p.workspace_id).with_for_update())
    if not s: s=Schedule(workspace_id=p.workspace_id);db.add(s)
    s.enabled=body.enabled;s.timezone=body.timezone;s.next_run_at=next_daily(utcnow(),body.timezone)
    db.flush();audit(db,p.user_id,p.workspace_id,'schedule.changed','schedule',s.id)
    return dict(enabled=s.enabled,timezone=s.timezone,next_run_at=s.next_run_at,hour=9)

@router.get('/automation-metrics')
def metrics(key=Depends(session),db=Depends(get_db,scope='function')):
    counts=dict(db.execute(select(Delivery.status,func.count()).where(Delivery.workspace_id==key).group_by(Delivery.status)).all())
    active=db.scalar(select(func.count()).select_from(Schedule).where(Schedule.workspace_id==key,Schedule.enabled.is_(True)))
    pulse=db.scalar(select(func.max(Job.heartbeat_at)).join(Event,Job.event_id==Event.id).where(Event.workspace_id==key))
    worker_pulse=db.scalar(select(func.max(WorkerHeartbeat.last_seen)))
    oldest=db.scalar(select(func.min(Job.run_after)).join(Event,Job.event_id==Event.id).where(Event.workspace_id==key,Job.status.in_(['queued','retry'])))
    expired=db.scalar(select(func.count()).select_from(Job).join(Event,Job.event_id==Event.id).where(Event.workspace_id==key,Job.status=='running',Job.lease_until<utcnow()))
    return dict(deliveries=counts,enabled_schedules=active,last_worker_activity=pulse,worker_alive=bool(worker_pulse and worker_pulse>utcnow()-timedelta(seconds=90)),oldest_due_age_seconds=max(0,int((utcnow()-oldest).total_seconds())) if oldest else 0,expired_leases=expired)

@router.get('/jobs/{job_id}')
def job(job_id:UUID,key=Depends(session),db=Depends(get_db,scope='function')):
    j=db.scalar(select(Job).join(Event,Job.event_id==Event.id).where(Job.id==job_id,Event.workspace_id==key))
    if not j: raise HTTPException(404,{'code':'job_missing'})
    return dict(id=str(j.id),event_id=str(j.event_id),status=j.status,attempts=j.attempts,run_after=j.run_after,lease_until=j.lease_until,heartbeat_at=j.heartbeat_at,max_attempts=j.max_attempts)

