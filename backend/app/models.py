from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('email = lower(btrim(email)) AND length(email) > 3',name='ck_user_email'),)

class Membership(Base):
    __tablename__ = 'workspace_memberships'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[object] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),unique=True)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id',ondelete='CASCADE'),index=True)
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__ = (CheckConstraint("role IN ('admin','operator','viewer')",name='ck_membership_role'),
        UniqueConstraint('id','workspace_id',name='uq_membership_scope'))

class AuthSession(Base):
    __tablename__ = 'sessions'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True,default=uuid4)
    membership_id: Mapped[object] = mapped_column(Uuid,index=True)
    workspace_id: Mapped[object] = mapped_column(Uuid)
    token_hash: Mapped[str] = mapped_column(String(64),unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (ForeignKeyConstraint(['membership_id','workspace_id'],['workspace_memberships.id','workspace_memberships.workspace_id'],ondelete='CASCADE',name='fk_session_membership_scope'),
        CheckConstraint('expires_at > created_at',name='ck_session_expiry'))

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[object] = mapped_column(Uuid,primary_key=True,default=uuid4)
    workspace_id: Mapped[object | None] = mapped_column(ForeignKey('workspaces.id',ondelete='CASCADE'))
    actor_id: Mapped[object | None] = mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__ = (Index('ix_audit_workspace_created','workspace_id','created_at','id'),)
class Workspace(Base):
    __tablename__ = 'workspaces'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
class Import(Base):
    __tablename__ = 'imports'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    filename: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default='uploaded')
    columns: Mapped[list] = mapped_column(JSONB, default=list)
    mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    total: Mapped[int] = mapped_column(Integer)
    valid: Mapped[int] = mapped_column(Integer, default=0)
    invalid: Mapped[int] = mapped_column(Integer, default=0)
    duplicate: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('uploaded','mapped','analyzed','completed')", name='ck_import_status'),
        CheckConstraint('total >= 0 AND valid >= 0 AND invalid >= 0 AND duplicate >= 0 AND inserted >= 0 AND inserted <= valid', name='ck_import_counts'),
        CheckConstraint("status NOT IN ('analyzed','completed') OR total = valid + invalid + duplicate", name='ck_import_partition'),
        CheckConstraint("(status = 'completed') = (committed_at IS NOT NULL)", name='ck_import_committed'),
        Index('ix_import_workspace_created', 'workspace_id', 'created_at', 'id'),)
class ImportRow(Base):
    __tablename__ = 'import_rows'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    import_id: Mapped[object] = mapped_column(ForeignKey('imports.id', ondelete='CASCADE'))
    row_number: Mapped[int] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSONB)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    classification: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('import_id','row_number',name='uq_row_number'),
        CheckConstraint('row_number >= 2',name='ck_row_number'),
        CheckConstraint("classification IS NULL OR classification IN ('valid','invalid','duplicate')",name='ck_row_classification'),
        Index('ix_row_import_classification','import_id','classification'))
class ValidationIssue(Base):
    __tablename__ = 'validation_issues'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    row_id: Mapped[object] = mapped_column(ForeignKey('import_rows.id', ondelete='CASCADE'), index=True)
    field: Mapped[str] = mapped_column(String(40))
    code: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('row_id','field','code',name='uq_issue'),)
class Lead(Base):
    __tablename__ = 'leads'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id',ondelete='CASCADE'))
    import_id: Mapped[object] = mapped_column(ForeignKey('imports.id',ondelete='RESTRICT'), index=True)
    source_row_id: Mapped[object | None] = mapped_column(ForeignKey('import_rows.id',ondelete='RESTRICT'), unique=True)
    email_normalized: Mapped[str] = mapped_column(String(320), unique=True)
    data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("email_normalized = lower(btrim(email_normalized)) AND length(email_normalized) > 0",name='ck_lead_email_normalized'),
        Index('ix_lead_workspace_created','workspace_id','created_at','id'),)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True)
    type: Mapped[str] = mapped_column(String(64))
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class IntegrationConfig(Base):
    __tablename__ = 'integration_configs'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    destination: Mapped[str] = mapped_column(String(2048), default='')
    credential_ref: Mapped[str] = mapped_column(String(128), default='')
    timeout: Mapped[int] = mapped_column(Integer, default=10)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    backoff: Mapped[int] = mapped_column(Integer, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint('workspace_id','kind', name='uq_integration_kind'), CheckConstraint("kind IN ('webhook','telegram')", name='ck_integration_kind'), CheckConstraint('timeout BETWEEN 1 AND 20 AND max_attempts BETWEEN 1 AND 10 AND backoff BETWEEN 1 AND 3600', name='ck_integration_policy'))

class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True)
    event_id: Mapped[object] = mapped_column(ForeignKey('events.id', ondelete='CASCADE'))
    integration_id: Mapped[object] = mapped_column(ForeignKey('integration_configs.id', ondelete='CASCADE'))
    status: Mapped[str] = mapped_column(String(16), default='queued')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    response_code: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint('event_id','integration_id',name='uq_event_delivery'), CheckConstraint("status IN ('queued','running','retry','delivered','failed','paused')",name='ck_delivery_status'))

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[object] = mapped_column(ForeignKey('events.id', ondelete='CASCADE'))
    delivery_id: Mapped[object | None] = mapped_column(ForeignKey('deliveries.id', ondelete='CASCADE'), unique=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(16), default='queued')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    backoff: Mapped[int] = mapped_column(Integer, default=30)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[object | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (Index('ix_job_claim','status','run_after','lease_until'), CheckConstraint("status IN ('queued','running','retry','completed','failed','paused')",name='ck_job_status'), CheckConstraint('attempts >= 0 AND max_attempts BETWEEN 1 AND 10',name='ck_job_attempts'))

class Schedule(Base):
    __tablename__ = 'schedules'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[object] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(64), default='UTC')
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class WorkerHeartbeat(Base):
    __tablename__ = 'worker_heartbeats'
    id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
