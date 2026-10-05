"""Idle worker liveness, independent of whether jobs exist."""
from alembic import op
import sqlalchemy as sa
revision = 'a5release00001'
down_revision = 'a4outbox000001'
branch_labels = depends_on = None

def upgrade():
    op.create_table('worker_heartbeats', sa.Column('id', sa.Uuid(), primary_key=True), sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_worker_heartbeats_last_seen', 'worker_heartbeats', ['last_seen'])

def downgrade():
    op.drop_table('worker_heartbeats')
