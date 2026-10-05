# Deployment readiness · 0.5.0-rc.1

No deployment performed. Static checks do not verify Docker/Compose execution.

## Environment matrix

| Setting | Dev | Test | Production |
|---|---|---|---|
| ASTRASYNQ_MODE | development | test | production |
| DB | astrasynq, loopback 55432 | astrasynq_test only | dedicated authenticated PostgreSQL |
| Cookies | Secure=false local HTTP, HttpOnly/lax | local HTTP fixtures | Secure=true, HttpOnly/lax or strict |
| Origins | explicit local UI/API | QA 4185/8012 | explicit same-origin HTTPS URLs |
| Private webhook override | false; explicit QA opt-in | temporary fixtures | forbidden |
| Docs routes | enabled | enabled | unavailable |
| Seed | local only | disposable synthetic | no automatic seed |
| Credentials | private env | synthetic mocks | private worker env/secret service |

Production validation rejects unsafe cookie/origin/DB/private-webhook config without exposing values. Remote DB requires sslmode=verify-full; special `db` hostname is private isolated Compose only. URI validation cannot inspect actual pg_hba.conf, privileges or isolation.

## Topology and migrations

Dev launcher: DB → alembic upgrade head → dev seed → API/worker/built frontend. Stop existing recorded session first. Installed build tools run offline; dependency installation still uses lockfile.

Compose: DB health → one-shot migrate → API readiness → worker/nginx. Backend UID 10001. Durable services restart unless-stopped; migration does not. Image API command does not migrate/seed. Outside Compose run migrations once before processes, never concurrent migrators. Head a5release00001, parent a4outbox000001, adds worker_heartbeats only.

Compose is loopback 8000/4173 dev smoke template, not complete public HTTPS hosting. Production requires restricted DB role/password, HTTPS origins/Secure cookies, edge TLS/HSTS/shared limits and private network. Never expose DB/reuse trust cluster. Use SCRAM and separate runtime/migration roles. Stock POSTGRES_USER is bootstrap superuser: provision restricted runtime role and adapt URLs/config before public exposure.

Approved rollout: immutable builds → backup/restore test → drain workers/restrict writes → migrate once → API readiness → fleet health → frontend/edge → auth/import/outbox/safe delivery smoke → open traffic. Private worker secrets supplied before start; no real external credentials used in M5.

## Edge security

UI/API same HTTPS origin; CORS absent. Edge enforces 6 MiB body before buffering, bounded upload/connection time, shared login/API limits and narrowly trusted proxy addresses. API also bounds multipart/CSV at 6/5 MiB and 10,000 rows. HSTS only verified HTTPS, minimum max-age=31536000, never local HTTP. API HSTS requires production plus effective HTTPS scheme. Trust forwarded-proto/IP only from configured proxy, not arbitrary clients.

Frontend CSP permits self scripts/fonts/images (including bundled data fonts) plus inline styles for motion/charts, no inline script/external connections. API production CSP denies content. Verify actual edge headers/error paths before exposure.

## Backup/restore

Dumps contain personal/auth data: encrypt, restrict access, store off-host, set retention/RPO/RTO, test restore. No secret DSN args; use protected password file/service credentials. No committed dumps.

```text
pg_dump -Fc --dbname=<private service> --file=<private staging path>
createdb <new isolated restore DB>
pg_restore --exit-on-error --no-owner --no-acl --dbname=<isolated target> <backup>
```

Record DB/tool versions, revision, counts/checksums and constraints. Start isolated restored app; check login/import/retry/roles. Never overwrite production for smoke. Privilege restore separate: no-owner/no-acl smoke does not prove role grants. DB dump excludes worker secrets.

scripts/verify-operations.py accepts only exact local project cluster 55432, dumps astrasynq_test, restores a newly created random DB, verifies revision/counts/lead checksum, drops only its new DB. Private backup/evidence in .local. Optional --restart-postgres checks live=200/ready=503 during stop, then API/worker reconnect and runtime preservation. Results in M5 report.

## Health/logs/alerts

API live: process independent of DB. Ready: actual DB plus exact head, 503 otherwise. Worker outage leaves imports/outbox durable, so not an API readiness prerequisite. Worker --health: any fleet pulse <90s including idle, not per-container identity. Supervise individual process separately; job heartbeat distinct.

Existing metrics: failed/pending deliveries, last job activity, fleet availability, oldest due age, expired leases. JSON request logs: generated ID/method/status/duration; worker: job/event IDs, safe error codes/attempts. No payload/header/query/secret logging. Disable raw access logs, apply infrastructure redaction/retention.

Alerts: DB/API readiness >30s; no fleet >90s; oldest due >5m; unexpected terminal failure; expired leases >120s; storage pressure; repeated login 429. Check credentials/receiver/budget before retry. Failed/paused remain visible.

## Retention/restart

Operator schedule after backups: python -m app.maintenance --days 90 --batch 100. No automatic runtime deletion. Bounds: 7..3650 days, 1..1000 histories/session/pulse records per invocation. Only old fully successful histories; active/retry/failed/paused/recently changed protected. Import event dedupe tombstones permanent, other old success events expire. Expired sessions/pulses same age policy. Leads/import/source rows/audit retained indefinitely for provenance; monitor growth and review privacy deletion separately. Request spools close at request/process lifetime; no application upload repository and no sweeping shared temp.

Crashes recover through leases, remote duplicate effects possible. Graceful stop budget covers in-flight policy. Windows launcher is dev helper, production needs service/container restart and independently supervised DB.

Built UI hides API-doc links by default; development server shows them. VITE_SHOW_API_DOCS=true can enable links only for a dev build where API docs are available; leave absent/false for public production builds.
