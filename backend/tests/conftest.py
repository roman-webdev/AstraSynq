import os
os.environ['ASTRASYNQ_MODE']='test'
from pathlib import Path
# Use an explicitly separate database; never truncate runtime data.
url=os.getenv('TEST_DATABASE_URL','postgresql+psycopg://astrasynq@127.0.0.1:55432/astrasynq_test')
if not url.rstrip('/').endswith('/astrasynq_test'):
    raise RuntimeError('Test database must be named astrasynq_test')
os.environ['DATABASE_URL']=url
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import text
from app.database import engine

@pytest.fixture(scope='session',autouse=True)
def migrated_database():
    command.upgrade(Config(str(Path(__file__).parents[1]/'alembic.ini')),'head')

@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    with engine.begin() as conn:
        conn.execute(text('TRUNCATE workspaces, users, imports, import_rows, validation_issues, leads, worker_heartbeats CASCADE'))
    from app.auth import attempts
    attempts.clear()
    yield
