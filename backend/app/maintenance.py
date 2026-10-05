"""Opt-in, bounded retention. Failed/paused/active work and import dedupe survive."""
import argparse
from datetime import timedelta
from sqlalchemy import select, delete, exists
from .database import SessionLocal
from .models import Event, Job, Delivery, AuthSession, WorkerHeartbeat, utcnow

def cleanup(db, days=90, batch=100):
    if not 7 <= days <= 3650 or not 1 <= batch <= 1000:
        raise ValueError('Retention requires days 7..3650 and batch 1..1000')
    cutoff = utcnow() - timedelta(days=days)
    unsafe_job = exists(select(Job.id).where(Job.event_id == Event.id, Job.status != 'completed'))
    unsafe_delivery = exists(select(Delivery.id).where(Delivery.event_id == Event.id, (Delivery.status != 'delivered') | (Delivery.updated_at >= cutoff)))
    has_job = exists(select(Job.id).where(Job.event_id == Event.id))
    events = list(db.scalars(select(Event).where(Event.created_at < cutoff, ~unsafe_job, ~unsafe_delivery, (Event.type != 'import.completed') | has_job).order_by(Event.created_at).limit(batch).with_for_update(skip_locked=True)))
    histories = 0
    for event in events:
        # Preserve import events as permanent dedupe tombstones. API commit is also idempotent.
        if event.type == 'import.completed':
            if db.scalar(select(Job.id).where(Job.event_id == event.id).limit(1)) is None:
                continue
            db.execute(delete(Job).where(Job.event_id == event.id))
            db.execute(delete(Delivery).where(Delivery.event_id == event.id))
        else:
            db.delete(event)
        histories += 1
    sessions = list(db.scalars(select(AuthSession.id).where(AuthSession.expires_at < cutoff).limit(batch).with_for_update(skip_locked=True)))
    if sessions:
        db.execute(delete(AuthSession).where(AuthSession.id.in_(sessions)))
    pulses = list(db.scalars(select(WorkerHeartbeat.id).where(WorkerHeartbeat.last_seen < cutoff).limit(batch).with_for_update(skip_locked=True)))
    if pulses:
        db.execute(delete(WorkerHeartbeat).where(WorkerHeartbeat.id.in_(pulses)))
    return {'event_histories': histories, 'sessions': len(sessions), 'worker_pulses': len(pulses)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--batch', type=int, default=100)
    args = parser.parse_args()
    from .observability import log
    with SessionLocal.begin() as db:
        result = cleanup(db, args.days, args.batch)
    log('retention.completed', **result)

if __name__ == '__main__':
    main()
