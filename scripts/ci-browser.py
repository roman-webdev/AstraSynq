"""Synthetic CI only; requires the isolated astrasynq_test PostgreSQL database."""
import os, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if not os.environ.get('TEST_DATABASE_URL','').endswith('/astrasynq_test'):
    raise SystemExit('Explicit isolated astrasynq_test database required')
env={**os.environ,'ASTRASYNQ_PYTHON':sys.executable,'ASTRASYNQ_PORTABLE_SMOKE':'1','ASTRASYNQ_PREVIEW_URL':'http://127.0.0.1:4185','ASTRASYNQ_IMMERSIVE_URL':'http://127.0.0.1:4185'}
logs=ROOT/'.clearance/ci';logs.mkdir(parents=True,exist_ok=True)
processes=[]
try:
    with (logs/'api.log').open('w') as api_log,(logs/'ui.log').open('w') as ui_log:
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8012','--no-access-log'],cwd=ROOT/'backend',env=env,stdout=api_log,stderr=api_log))
        processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','preview','--configLoader','native','--host','127.0.0.1','--port','4185','--strictPort'],cwd=ROOT/'frontend',env=env,stdout=ui_log,stderr=ui_log))
        for attempt in range(120):
            if any(p.poll() is not None for p in processes):raise RuntimeError('CI server exited')
            try:
                with urllib.request.urlopen('http://127.0.0.1:4185/health/ready',timeout=2) as response:
                    if response.status==200:break
            except Exception:time.sleep(.5)
        else:raise RuntimeError('CI server readiness timeout')
        subprocess.run(['node','--test','tests/i18n.e2e.mjs'],cwd=ROOT/'frontend',env=env,check=True)
        subprocess.run(['node','--test','--test-name-pattern=reduced motion:|WebGL unavailable:|save-data preference','tests/immersive.e2e.mjs'],cwd=ROOT/'frontend',env=env,check=True)
finally:
    for p in processes:
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
