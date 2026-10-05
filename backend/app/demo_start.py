"""Demo-only start gate: validate, migrate, idempotently seed, serve one process."""
import os
from pathlib import Path
from alembic import command
from alembic.config import Config
from .config import demo_mode, validate_environment

def main():
    validate_environment()
    if not demo_mode(): raise SystemExit('This entrypoint requires synthetic demo mode')
    root=Path(__file__).parents[1]
    command.upgrade(Config(str(root/'alembic.ini')),'head')
    from .demo import seed
    from .database import SessionLocal
    with SessionLocal.begin() as db: seed(db,os.environ['ASTRASYNQ_DEMO_PASSWORD'])
    import uvicorn
    host='127.0.0.1' if os.getenv('ASTRASYNQ_MODE')=='test' else '0.0.0.0'
    uvicorn.run('app.main:app',host=host,port=int(os.getenv('PORT','8000')),
                workers=1,proxy_headers=False,access_log=False,limit_concurrency=20)

if __name__=='__main__': main()
