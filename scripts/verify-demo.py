"""Local synthetic browser check; isolated astrasynq_test DB only, never deployment."""
import os, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
url=os.environ.get('TEST_DATABASE_URL','')
if not url.endswith('/astrasynq_test'): raise SystemExit('Explicit astrasynq_test database required')
env={**os.environ,'DATABASE_URL':url,'ASTRASYNQ_MODE':'test','ASTRASYNQ_DEMO_MODE':'true',
     'AUTH_COOKIE_SECURE':'false','AUTH_SESSION_HOURS':'1','AUTH_ALLOWED_ORIGINS':'http://127.0.0.1:8013',
     'ASTRASYNQ_DEMO_STATIC_DIR':str(ROOT/'frontend/dist/client'),'PORT':'8013',
     'ASTRASYNQ_DEMO_PASSWORD':'Synthetic isolated browser password 42!'}
# Refuse a non-demo frontend build before resetting even the isolated database.
assets=list((ROOT/'frontend/dist/client/assets').glob('*.js'))
if not any('demo-label-full' in p.read_text(encoding='utf-8') for p in assets):
    raise SystemExit('Build frontend with VITE_ASTRASYNQ_DEMO_MODE=true first')
subprocess.run([sys.executable,'-c',
    "from app.database import engine,SessionLocal;from sqlalchemy import text;"
    "from app.demo import seed;import os;"
    "conn=engine.connect();conn.execute(text('TRUNCATE workspaces, users, worker_heartbeats, audit_logs CASCADE'));conn.commit();conn.close();"
    "db=SessionLocal();seed(db,os.environ['ASTRASYNQ_DEMO_PASSWORD']);db.commit();db.close()"],cwd=ROOT/'backend',env=env,check=True)
logs=ROOT/'work/demo-qa';logs.mkdir(parents=True,exist_ok=True)
with (logs/'server.log').open('w') as log:
    proc=subprocess.Popen([sys.executable,'-m','app.demo_start'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
    try:
        for _ in range(60):
            if proc.poll() is not None: raise RuntimeError('Demo server exited')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8013/health/live',timeout=2) as r:
                    if r.status==200: break
            except Exception: time.sleep(.2)
        else: raise RuntimeError('Demo startup timed out')
        subprocess.run(['node','scripts/demo-browser.mjs'],cwd=ROOT,env=env,check=True)
        subprocess.run(['node','--test','tests/demo-ui.e2e.mjs'],cwd=ROOT/'frontend',env={**env,'ASTRASYNQ_DEMO_UI_URL':'http://127.0.0.1:8013'},check=True)
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
