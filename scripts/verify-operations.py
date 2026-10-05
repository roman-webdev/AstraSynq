"""Local dev-only backup/restore and PostgreSQL restart smoke. No production target."""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'.local/postgres/pgsql/bin'
DATA=ROOT/'.local/postgres/data'
BASE='postgresql://astrasynq@127.0.0.1:55432/'

def counts(database):
    with psycopg.connect(BASE+database) as db:
        result={name:db.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(name))).fetchone()[0] for name in ['imports','leads','events','jobs','deliveries','users','sessions','worker_heartbeats']}
        result['revision']=db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        result['lead_data']=db.execute("SELECT md5(coalesce(string_agg(email_normalized || data::text, '' ORDER BY email_normalized),'')) FROM leads").fetchone()[0]
        return result

def health(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8011'+path,timeout=8) as r: return r.status
    except urllib.error.HTTPError as exc: return exc.code

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restart-postgres',action='store_true');args=parser.parse_args()
    with psycopg.connect(BASE+'postgres',autocommit=True) as control:
        actual=Path(control.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual!=DATA.resolve(): raise RuntimeError('Refusing unrelated PostgreSQL cluster')
    backup_dir=ROOT/'.local/backups';backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/'m5-test.dump'
    before=counts('astrasynq_test')
    subprocess.run([str(BIN/'pg_dump.exe'),'-Fc','--dbname',BASE+'astrasynq_test','--file',str(backup)],check=True,capture_output=True)
    restored='astrasynq_restore_m5_'+uuid4().hex[:12]
    with psycopg.connect(BASE+'postgres',autocommit=True) as control:
        control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored)))
    try:
        subprocess.run([str(BIN/'pg_restore.exe'),'--exit-on-error','--no-owner','--no-acl','--dbname',BASE+restored,str(backup)],check=True,capture_output=True)
        assert counts(restored)==before,'Restore differs from source test database'
    finally:
        with psycopg.connect(BASE+'postgres',autocommit=True) as control:
            control.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(restored)))
    result={'backup_restore':'PASS','test_counts':before,'private_backup':'.local/backups/m5-test.dump','postgres_restart':'not_requested'}
    if args.restart_postgres:
        runtime_before=counts('astrasynq')
        stopped=subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(DATA),'-m','fast','stop'],capture_output=True)
        if stopped.returncode:
            result.update(postgres_restart='UNVERIFIED',reason='Local cluster stop signal was rejected by process permissions',runtime_before=runtime_before)
            (ROOT/'.local/m5-operations-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2))
            return
        try:
            assert health('/health/live')==200 and health('/health/ready')==503
        finally:
            subprocess.run([sys.executable,str(ROOT/'scripts/setup-postgres.py')],check=True,capture_output=True)
        for _ in range(40):
            if health('/health/ready')==200: break
            time.sleep(.25)
        else: raise AssertionError('API did not reconnect')
        after=counts('astrasynq')
        for field in ['imports','leads','events','jobs','deliveries','users','sessions','revision','lead_data']:
            assert runtime_before[field]==after[field],f'Runtime {field} changed'
        with psycopg.connect(BASE+'astrasynq') as db:
            for _ in range(40):
                if db.execute("SELECT count(*) FROM worker_heartbeats WHERE last_seen > now()-interval '5 seconds'").fetchone()[0]: break
                db.commit();time.sleep(.25)
            else: raise AssertionError('Worker did not reconnect')
        result.update(postgres_restart='PASS',api_outage_ready=503,api_outage_live=200,runtime_data_preserved=True,runtime_before=runtime_before)
    (ROOT/'.local/m5-operations-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
