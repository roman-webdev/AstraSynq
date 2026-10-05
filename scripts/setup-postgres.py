"""Provision a project-local development cluster; no service/admin installation."""
import argparse
import hashlib
import shutil
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'.local'/'postgres'
BIN=LOCAL/'pgsql'/'bin'
DATA=LOCAL/'data'
URL='https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip'
SHA256='25e6fcdfb8caec38691bf461125e7564508760666f7b8e5dc6a5f0818f58f81e'
DSN='postgresql://astrasynq@127.0.0.1:55432/postgres'

def run(name,*args): subprocess.run([str(BIN/(name+'.exe')),*map(str,args)],check=True,cwd=ROOT)
def connected():
    try:
        with psycopg.connect(DSN,connect_timeout=1): return True
    except psycopg.OperationalError: return False

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stop',action='store_true');args=parser.parse_args()
    if args.stop:
        if (DATA/'postmaster.pid').exists(): run('pg_ctl','-D',DATA,'-m','fast','stop')
        return
    LOCAL.mkdir(parents=True,exist_ok=True)
    if not (BIN/'postgres.exe').exists():
        archive=LOCAL/'binaries.zip'
        if not archive.exists():
            with urllib.request.urlopen(URL) as source, archive.open('wb') as target: shutil.copyfileobj(source,target)
        if hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()!=SHA256:
            raise RuntimeError('PostgreSQL archive differs from the verified development archive')
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.startswith(('pgsql/bin/','pgsql/lib/','pgsql/share/')): z.extract(name,LOCAL)
    if not (DATA/'PG_VERSION').exists():
        if DATA.exists(): raise RuntimeError('Incomplete cluster; inspect .local/postgres/data before retrying')
        run('initdb','-D',DATA,'-U','astrasynq','--auth=trust','--encoding=UTF8','--locale=C')
        with (DATA/'postgresql.conf').open('a') as f: f.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\ntimezone = 'UTC'\n")
    if not connected():
        # Direct launch avoids restricted-token failures of pg_ctl in Codex sandbox.
        with (LOCAL/'postgres.log').open('ab') as log:
            process=subprocess.Popen([str(BIN/'postgres.exe'),'-D',str(DATA)],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(50):
            if connected(): break
            if process.poll() is not None: raise RuntimeError('PostgreSQL exited; inspect .local/postgres/postgres.log')
            time.sleep(.2)
        else: raise RuntimeError('PostgreSQL readiness timed out')
    # Refuse to modify an unrelated service already listening on the chosen port.
    with psycopg.connect(DSN,autocommit=True) as db:
        actual=Path(db.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual!=DATA.resolve(): raise RuntimeError('Port 55432 belongs to a different PostgreSQL cluster')
        for name in ['astrasynq','astrasynq_test']:
            if not db.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone():
                db.execute('CREATE DATABASE '+name)
    print('PostgreSQL ready on 127.0.0.1:55432; runtime/test databases are separate')
if __name__=='__main__': main()
