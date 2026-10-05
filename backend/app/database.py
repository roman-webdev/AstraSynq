"""PostgreSQL configuration; no implicit SQLite fallback or schema creation."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
load_dotenv(Path(__file__).resolve().parents[2] / '.env')
from .config import validate_environment
validate_environment()
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://astrasynq@127.0.0.1:55432/astrasynq')
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
if not DATABASE_URL.startswith('postgresql+psycopg://'):
    raise RuntimeError('AstraSynq runtime requires PostgreSQL (psycopg)')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'options':'-c timezone=UTC', 'connect_timeout':5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)
def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
