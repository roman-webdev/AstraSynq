"""Run with python -m app.worker. At-least-once transport; lease-token fenced writes."""
import argparse, signal, threading, time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, or_, update
from .database import SessionLocal
from .models import Job, Delivery, Event, IntegrationConfig, WorkerHeartbeat, utcnow
from sqlalchemy.dialects.postgresql import insert
from .observability import log
from .automation import send, schedule_due
from .auth import audit
LEASE_SECONDS=60
WORKER_ID=uuid4()

def pulse():
    with SessionLocal.begin() as db:
        db.execute(insert(WorkerHeartbeat).values(id=WORKER_ID,last_seen=utcnow()).on_conflict_do_update(index_elements=['id'],set_={'last_seen':utcnow()}))

def live():
    with SessionLocal() as db:
        return db.scalar(select(WorkerHeartbeat.id).where(WorkerHeartbeat.last_seen>utcnow()-timedelta(seconds=90)).limit(1)) is not None


def terminal(db,job,delivery,code='attempts_exhausted'):
    job.status='failed';job.lease_until=None;job.lease_token=None
    if delivery:
        delivery.status='failed';delivery.last_error=code;delivery.updated_at=utcnow()
        audit(db,None,delivery.workspace_id,'delivery.failed','delivery',delivery.id)
        log('delivery.failed',job_id=job.id,event_id=job.event_id,error=code,attempts=job.attempts)


def claim():
    with SessionLocal.begin() as db:
        now=utcnow()
        job=db.scalar(select(Job).where(or_((Job.status.in_(['queued','retry'])) & (Job.run_after<=now),(Job.status=='running') & (Job.lease_until<=now))).order_by(Job.run_after,Job.id).with_for_update(skip_locked=True).limit(1))
        if not job: return None
        delivery=db.get(Delivery,job.delivery_id) if job.delivery_id else None
        if job.attempts>=job.max_attempts:
            terminal(db,job,delivery);return None
        job.status='running';job.attempts+=1;job.lease_token=uuid4();job.lease_until=now+timedelta(seconds=LEASE_SECONDS);job.heartbeat_at=now
        if delivery: delivery.status='running';delivery.attempts+=1;delivery.updated_at=now
        return job.id,job.lease_token


def heartbeat(ident,token):
    with SessionLocal.begin() as db:
        now=utcnow()
        return db.execute(update(Job).where(Job.id==ident,Job.lease_token==token,Job.status=='running',Job.lease_until>now).values(heartbeat_at=now,lease_until=now+timedelta(seconds=LEASE_SECONDS))).rowcount==1


def finish(ident,token,code,error):
    with SessionLocal.begin() as db:
        job=db.scalar(select(Job).where(Job.id==ident,Job.lease_token==token,Job.status=='running',Job.lease_until>utcnow()).with_for_update())
        if not job: return False
        d=db.get(Delivery,job.delivery_id)
        d.response_code=code;d.last_error=error;d.updated_at=utcnow()
        if not error:
            job.status='completed';d.status='delivered';d.delivered_at=utcnow()
        elif job.attempts>=job.max_attempts: terminal(db,job,d,error)
        else:
            job.status=d.status='retry';job.run_after=utcnow()+timedelta(seconds=min(86400,job.backoff*2**(job.attempts-1)))
        job.lease_until=None;job.lease_token=None
        log('delivery.finished',job_id=ident,event_id=job.event_id,status=job.status,error=error,attempts=job.attempts)
        return True


def process_one():
    acquired=claim()
    if not acquired: return False
    ident,token=acquired
    with SessionLocal() as db:
        job=db.get(Job,ident);d=db.get(Delivery,job.delivery_id);cfg=db.get(IntegrationConfig,d.integration_id);event=db.get(Event,job.event_id)
        if not cfg.enabled and event.type!='integration.test':
            with SessionLocal.begin() as write:
                j=write.scalar(select(Job).where(Job.id==ident,Job.lease_token==token).with_for_update())
                if j and j.status=='running' and j.lease_until>utcnow(): j.status='paused';j.lease_until=None;j.lease_token=None;write.get(Delivery,j.delivery_id).status='paused'
            return True
        stop=threading.Event()
        def pulse():
            while not stop.wait(10):
                try:
                    if not heartbeat(ident,token): return
                except Exception: return
        thread=threading.Thread(target=pulse,daemon=True);thread.start()
        try:
            code,error=send(cfg,event)
            finish(ident,token,code,error)
        finally: stop.set();thread.join(timeout=1)
    return True


def tick():
    pulse()
    with SessionLocal.begin() as db: schedule_due(db)
    return process_one()


def main():
    from .config import demo_mode
    if demo_mode(): raise SystemExit('Synthetic demo has no persistent worker; commits use an internal mock sink.')
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');parser.add_argument('--health',action='store_true');args=parser.parse_args()
    if args.health:
        raise SystemExit(0 if live() else 1)
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,lambda *_:stop.set())
    while not stop.is_set():
        try: worked=tick()
        except Exception:
            # Do not print exception strings: HTTP errors may contain credential URLs.
            log('worker.cycle_failed',worker_id=WORKER_ID);worked=False
        if args.once: break
        if not worked: stop.wait(1)
if __name__=='__main__': main()
