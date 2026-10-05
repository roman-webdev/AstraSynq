"""Durable outbox and safe, pinned-address HTTP transport. Credentials live in env."""
import hashlib, hmac, http.client, ipaddress, json, os, re, socket, ssl
from datetime import timedelta, datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from fastapi import HTTPException
from .models import Event, Job, Delivery, IntegrationConfig, Schedule, Import, utcnow


def emit(db, scope, kind, dedupe, payload, configs=None):
    ident = db.scalar(insert(Event).values(id=uuid4(),workspace_id=scope,type=kind,dedupe_key=dedupe,payload=payload).on_conflict_do_nothing(index_elements=['dedupe_key']).returning(Event.id))
    if ident is None:
        return db.scalar(select(Event.id).where(Event.dedupe_key==dedupe))
    # Snapshot recipients at commit time; future enablement does not replay old imports.
    if configs is None:
        configs=list(db.scalars(select(IntegrationConfig).where(IntegrationConfig.workspace_id==scope,IntegrationConfig.enabled.is_(True))))
    for cfg in configs:
        delivery=Delivery(id=uuid4(),workspace_id=scope,event_id=ident,integration_id=cfg.id)
        db.add(delivery);db.flush()
        db.add(Job(event_id=ident,delivery_id=delivery.id,dedupe_key=f'delivery:{delivery.id}',max_attempts=cfg.max_attempts,backoff=cfg.backoff))
    # Persist a completed routing job even when no recipients are enabled.
    db.add(Job(event_id=ident,dedupe_key=f'route:{ident}',status='completed'))
    db.flush()
    return ident


def validate_ref(ref):
    if not re.fullmatch(r'ASTRASYNQ_CREDENTIAL_[A-Z0-9_]{1,96}',ref):
        raise ValueError('credential_reference_invalid')


def resolve_url(url):
    parsed=urlsplit(url)
    dev=os.getenv('ASTRASYNQ_MODE','production')=='development' and os.getenv('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS','false').lower()=='true'
    if parsed.scheme not in (('http','https') if dev else ('https',)) or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query or len(url)>2048:
        raise ValueError('webhook_url_invalid')
    port=parsed.port or (443 if parsed.scheme=='https' else 80)
    addresses=socket.getaddrinfo(parsed.hostname,port,type=socket.SOCK_STREAM)
    if not addresses or (not dev and any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses)):
        raise ValueError('webhook_address_forbidden')
    return parsed,addresses[0][4][0],port


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,ip,port,timeout):
        super().__init__(host,port,timeout=timeout,context=ssl.create_default_context());self.ip=ip
    def connect(self):
        sock=socket.create_connection((self.ip,self.port),self.timeout)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)


def post(url,body,headers,timeout):
    from .config import demo_mode
    if demo_mode(): raise ValueError('demo_egress_disabled')
    parsed,ip,port=resolve_url(url)
    conn=PinnedHTTPS(parsed.hostname,ip,port,timeout) if parsed.scheme=='https' else http.client.HTTPConnection(ip,port,timeout=timeout)
    try:
        # Connect only to the validated IP. Never follow redirects or environment proxies.
        headers={**headers,'Host':parsed.netloc,'Content-Type':'application/json'}
        conn.request('POST',parsed.path or '/',body=body,headers=headers)
        response=conn.getresponse()
        return response.status,response.read(65536)
    finally: conn.close()


def signature(secret,stamp,event_id,body):
    return 'sha256='+hmac.new(secret.encode(),stamp.encode()+b'.'+event_id.encode()+b'.'+body,hashlib.sha256).hexdigest()


def send(cfg,event):
    from .config import demo_mode
    if demo_mode(): return None,'demo_egress_disabled'
    validate_ref(cfg.credential_ref)
    secret=os.getenv(cfg.credential_ref,'')
    if not secret: return None,'credential_missing'
    payload={'event_id':str(event.id),'type':event.type,'time':event.created_at.isoformat(),'data':event.payload}
    try:
        if cfg.kind=='webhook':
            body=json.dumps(payload,sort_keys=True,separators=(',',':')).encode();stamp=str(int(utcnow().timestamp()))
            code,_=post(cfg.destination,body,{'X-AstraSynq-Event-ID':str(event.id),'X-AstraSynq-Timestamp':stamp,'X-AstraSynq-Signature':signature(secret,stamp,str(event.id),body)},cfg.timeout)
            return code,None if 200<=code<300 else 'http_non_2xx'
        if not re.fullmatch(r'[0-9]{1,20}:[A-Za-z0-9_-]{20,160}',secret): return None,'credential_invalid'
        data=event.payload
        message=f"AstraSynq {event.type}\nImport: {data.get('import_id','—')}\nStatus: {data.get('status','summary')} | total {data.get('total',0)} | inserted {data.get('inserted',0)} | invalid {data.get('invalid',0)} | duplicates {data.get('duplicate',0)}\n{event.created_at.isoformat()}"
        code,response=post('https://api.telegram.org/bot'+secret+'/sendMessage',json.dumps({'chat_id':cfg.destination,'text':message}).encode(),{},cfg.timeout)
        if 200<=code<300:
            try: ok=json.loads(response).get('ok') is True
            except (ValueError,AttributeError): ok=False
            return code,None if ok else 'telegram_rejected'
        return code,'http_non_2xx'
    except (TimeoutError,socket.timeout): return None,'timeout'
    except (OSError,ValueError,http.client.HTTPException): return None,'transport_error'


def next_daily(now,tz):
    local=now.astimezone(ZoneInfo(tz))
    candidate=datetime.combine(local.date(),datetime.min.time(),ZoneInfo(tz)).replace(hour=9)
    if candidate<=local: candidate+=timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def schedule_due(db,now=None):
    from .config import demo_mode
    if demo_mode(): return
    now=now or utcnow()
    for s in db.scalars(select(Schedule).where(Schedule.enabled.is_(True),Schedule.next_run_at<=now).with_for_update(skip_locked=True)):
        due=s.next_run_at
        counts=db.execute(select(func.count(),func.coalesce(func.sum(Import.total),0),func.coalesce(func.sum(Import.inserted),0),func.coalesce(func.sum(Import.invalid),0),func.coalesce(func.sum(Import.duplicate),0)).where(Import.workspace_id==s.workspace_id,Import.committed_at>due-timedelta(days=1),Import.committed_at<=due)).one()
        emit(db,s.workspace_id,'summary.daily',f'summary:{s.id}:{due.isoformat()}',dict(status='summary',imports=counts[0],total=counts[1],inserted=counts[2],invalid=counts[3],duplicate=counts[4],period_end=due.isoformat()))
        s.next_run_at=next_daily(now,s.timezone)
