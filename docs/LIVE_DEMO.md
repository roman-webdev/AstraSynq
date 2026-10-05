# Live Synthetic Demo (Release Candidate, not production-ready)

**[Live synthetic demo](https://astrasynq-synthetic-demo.onrender.com)** — verified 2026-10-05.

Render service `astrasynq-synthetic-demo`: Free Docker, Frankfurt, main; deployed commit `41c7f161bb6570b608acafd0cf4ae83a4841bdaa`. Neon project `astrasynq-synthetic-demo`: Free, AWS Frankfurt, database `astrasynq_demo`, 0.25 CU, scale-to-zero after five minutes. No card or paid resource was added. `v0.5.0-rc.1` remains unchanged.

## Live verification evidence and limits

- PASS: Docker build/deploy, startup migrations and idempotent synthetic seed, HTTPS redirect, readiness, data preserved across redeploy.
- PASS: WebGL landing, reduced-motion and unavailable-WebGL fallback; invitation login; reload/logout/login; EN/UA/RU banner and workspace; mobile 390 × 844 smoke.
- PASS: exact sample upload → analyze (2 valid / 2 invalid / 1 duplicate) → commit two leads; subsequent sample dedupe; dashboard records, mock sink deliveries and `demo.delivery.simulated` audit.
- PASS: Secure/HttpOnly/SameSite=Lax one-hour session; preauth and session CSRF; same-origin mutation succeeds, foreign origin/wrong token blocked; anonymous/admin/config/test/retry/reset operations blocked; no public API docs, no wildcard CORS; CSP/HSTS/frame-denial/nosniff and API no-store.
- PASS: modified CSV rejected without echoed input; normal and chunked oversized bodies rejected; shared minute budget produced 429. HTML conditional 304 reload retains the existing same-origin UI CSP.
- Hosted CI PASS: production startup guards, workspace isolation, 30-import cap, daily request budget and quota persistence. Live quotas were not exhausted for the import/day caps; destructive offline reset and deliberate live DB outage were not performed.
- No real Telegram/webhook credentials, persistent worker or outbound integration sends were used. Reviewed public responses contain synthetic data; host logs record request metadata without bodies/secrets. Invitation password remains private in Render environment; this document contains no credentials.

Login: open the workspace, use `demo@example.test` and request temporary access from the owner. The owner retrieves `ASTRASYNQ_DEMO_PASSWORD` privately from Render; never publish it. Shared records and recent audit history change between reviewers. The exact sample can have zero new valid rows after earlier commits. Free cold starts, request limits and the 30-import cap constrain availability; owner reset requires the private procedure below. This is a portfolio demonstration, not production readiness evidence or an SLA.

The original preparation below is retained as the operator runbook. Provider configuration was created through `render.demo.yaml`; startup/build commands remain repository-defined. Portfolio and external profile updates require separate approval.

## Architecture

```text
Recruiter browser
  | HTTPS, same origin, invitation login
  v
Render Free web service (single instance/process, 512 MB)
  |-- React/Vite static build; immersive landing + synthetic banner
  |-- FastAPI: existing sessions, RBAC, CSRF, import lifecycle
  |-- demo-only bounded mock completion during commit (max 10 jobs)
  |        `-- internal synthetic sink; no HTTP/Telegram sending
  | PostgreSQL TLS verify-full
  v
Neon Free dedicated synthetic database
  imports/leads/outbox/jobs/mock deliveries/sessions/audit

No daemon worker, timed schedule, cron service, public reset or keepalive.
```

The normal deployment remains `frontend -> API -> PostgreSQL durable outbox -> separate app.worker -> HTTPS webhook/Telegram`, with lease fencing, retry/backoff and scheduled summaries. See [architecture](architecture.md), [automation](automation.md) and [production deployment](DEPLOYMENT.md). Demo mock completion is not evidence of production worker reliability, delivery confirmation or scheduler availability. Real architecture files and worker behavior outside demo mode are preserved.

The recommended stack costs $0 within quotas and uses provider subdomains. Hosting alternatives, dated official evidence and unresolved provider details are in [HOSTING_RESEARCH.md](HOSTING_RESEARCH.md).

## Demo security boundaries

- `ASTRASYNQ_DEMO_MODE=true` is allowed only with production guards or isolated test mode. Public host uses `ASTRASYNQ_MODE=production`. Never use development mode on the public host.
- Dedicated DB, fixed synthetic workspace and one `demo@example.test` operator; no shared public password. Render generates the password as a host secret. Owner shares temporary access privately with selected reviewers and rotates/resets between review periods. This task does not send credentials or invitations.
- Existing opaque server sessions, hashed stored tokens, HttpOnly/Secure cookies, SameSite=Lax, one-hour expiry, origin checks and session CSRF remain enforced. Frontend `/api/v1` is relative to the same HTTPS origin; no cross-site cookies or permissive CORS required.
- Any foreign workspace, different user or admin/viewer membership is rejected while demo mode is active. Admin bootstrap is disabled. No anonymous write path. No public reset endpoint.
- Only exact bytes of `backend/samples/demo.csv` accepted: reserved `.test` emails, synthetic names/companies, fixed invalid/duplicate examples. Arbitrary personal data/extra columns/file changes rejected before persistence. Original upload filename is replaced with `synthetic-demo.csv`. Seed uses distinct synthetic baseline emails so the first sample adds two records; subsequent imports demonstrate dedupe.
- Mutation allowlist: login/logout, sample import, mapping, analyze, commit only. User management, integration configuration/test/retry, schedules, deletion and unknown mutations are blocked. Existing read RBAC remains active; audit is visible to operator. No secrets exist in integration configs.
- No credential environment variables with non-empty values accepted; private webhook override forbidden. Network transport functions also reject demo mode, even if called outside HTTP routes. `app.worker` refuses startup; scheduler returns without emitting work. Internal mock writes mark `synthetic_sink`, no HTTP response status, and explicit synthetic audit action. UI banner and automation view disclose simulation.
- Shared PostgreSQL advisory-lock budget: 120 accepted API/readiness requests per rolling minute and 2,000 per rolling day, including failed/unauthenticated calls. Contending reservation returns 429; DB failures fail closed. Anonymous budget rows contain no IP, URL, email or request content and expire after 24 h. Original login limiter (10/min/process/IP, no forwarded-IP trust) remains an additional bound.
- Maximum 30 stored imports including seed, serialized by workspace DB lock; 5 rows/sample, two baseline leads + at most two sample leads. No arbitrary user or config creation. Demo request body limit 16 KiB for POST/PUT/PATCH, including chunked uploads; Uvicorn concurrency limit 20. Retained sessions/audit may accumulate within request limits until owner reset; reset weekly or before review sessions and monitor DB storage.
- Existing production SSRF controls stay in place: public address validation, HTTPS, pinned destination, verified certificates, no redirects/proxies. Demo sends no network integrations. API exceptions and validation responses hide submitted input; logging records event metadata/request IDs, not passwords, CSV or credentials. Provider infrastructure may log visitor IPs; no promise of zero infrastructure telemetry.
- Production docs/OpenAPI remain disabled. API CSP remains strict; demo HTML receives the existing self-only frontend CSP, frame denial, nosniff/referrer headers and HSTS. Application access logs disabled. Public host must redirect HTTP to HTTPS; check this after deployment.

The shared demo budget does not upgrade standard production to a distributed authentication limiter. Production shared rate limiting remains a documented blocker. This sandbox is bounded and invitation-only, but quota exhaustion/DoS remains possible; pause the service if abused. No paid overage exposure is authorized.

## Environment matrix

Names only in this table; enter secret values directly in host secret settings, never a committed `.env`, command history, build argument or frontend VITE variable.

| Name | Required where | Classification |
| --- | --- | --- |
| `DATABASE_URL` | API/migration/seed | Host secret; dedicated Neon role/password, TLS verification |
| `ASTRASYNQ_DEMO_PASSWORD` | API startup and offline reset | Generated host secret, 24..256 chars; invitation-only operator access |
| `ASTRASYNQ_MODE` | API | Required public production guard |
| `ASTRASYNQ_DEMO_MODE` | API | Required explicit demo flag |
| `AUTH_COOKIE_SECURE` | API | Required public HTTPS setting |
| `AUTH_COOKIE_SAMESITE` | API | Required existing same-origin policy |
| `AUTH_SESSION_HOURS` | API | Required one-hour demo expiry |
| `AUTH_ALLOWED_ORIGINS` | API | Exact public HTTPS origin, no path/wildcard; additional owned origin only after review |
| `ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS` | API | Required disabled override |
| `ASTRASYNQ_DEMO_STATIC_DIR` | API image | Fixed path supplied by Docker image |
| `VITE_ASTRASYNQ_DEMO_MODE` | Frontend build only | Nonsecret banner flag, enabled in demo Docker build |
| `PORT` | API | Provider-supplied listening port |
| `TEST_DATABASE_URL` | Local/CI QA only | Isolated test DB; never public-host config |
| `ASTRASYNQ_API_URL` | Local Vite QA only | Development reverse proxy target; not needed on demo host |
| `ASTRASYNQ_CREDENTIAL_*` | Neither demo API nor worker | Must be absent/empty; no Telegram token/webhook secret |
| `ASTRASYNQ_ADMIN_EMAIL`, `ASTRASYNQ_ADMIN_PASSWORD`, `ASTRASYNQ_WORKSPACE_ID` | Neither demo host | Do not bootstrap an admin |

Neon connection: use its direct endpoint with `postgresql+psycopg`, `sslmode=verify-full`, `sslrootcert=system` and small compute. Current local bundled libpq is 18 and supports system roots. Confirm the built image has system CA certificates and can verify Neon before publication. Provider `sslmode=require` alone does not satisfy AstraSynq production guards. Use a dedicated least-privilege app role after migrations if operationally feasible; current entrypoint needs schema migration rights, so do not reuse a production role/database. No remote TLS connection was made during prep.

## Deployment order (requires approval first)

1. Review local diff/tests and approve publishing a new main commit and deployment to Render Free + Neon Free. Do not move/recreate the RC tag. Check signups allow Free without a payment method; stop if signup requires paid upgrade/card outside the approved scope.
2. Create one dedicated Neon Free project in a region near Frankfurt; set small compute/scale-to-zero and confirm current Free allowances. No real data or existing DB connection. Copy its connection credential directly to Render host secrets with verify-full/system root configuration.
3. Create Render Hobby/Free web using `render.demo.yaml` (custom Blueprint path), root build context and `backend/Dockerfile.demo`. `autoDeployTrigger: off`; no worker, cron, Render DB, disk, paid plan or keepalive. Approve account integration only for `roman-webdev/AstraSynq`.
4. Before startup, set exact assigned HTTPS `onrender.com` origin in `AUTH_ALLOWED_ORIGINS`, database secret and generated operator password. Confirm all required matrix names. Never expose credentials in screenshots/logs/docs. Leave all integration credentials absent.
5. Image builds frontend with banner; non-root Python runtime starts `python -m app.demo_start`: validates production config, runs `alembic upgrade head`, checks dedicated database, idempotently seeds operator/baseline/mock config, starts one Uvicorn process. Failures stop startup; no API serves before migration/seed success. No pre-deploy hook (paid-only feature dependency) is required.
6. Render health check `/health/live` is DB-free to avoid keeping Neon compute active. Independently check `/health/ready` against expected schema `a5release00001`; 503 means not ready. Keep readiness checks infrequent; they consume demo budget. A successful process liveness does not establish DB readiness.
7. Verify checklist below, then privately give the generated temporary password to an invited reviewer. Publish a live URL in README only after actual successful deployment and separate review. No production claims.

## Seed/reset and start/stop

`python -m app.demo` is idempotent and never prints credentials. Startup does not reset data on cold starts. A changed password requires explicit offline reset; no silent rotation of existing credentials.

Owner reset: pause/stop Render first, use the same dedicated DB and temporary host secret in a private operator process, validate `ASTRASYNQ_MODE=production`/demo guards, then run from backend:

```text
python -m app.demo --reset
```

This checks that no foreign workspace or user exists, removes scoped leads before FK cascades, removes/reseeds the synthetic workspace/operator, revokes existing sessions by cascade, and recreates baseline/mock deliveries. It does not truncate unrelated tables or grant anonymous reset. Anonymous request-budget rows intentionally survive reset until expiry. Restart Render with the matching generated password; remove temporary local secret variables. Free Render has no shell/one-off jobs: use a private local operator connection after approval, not a public HTTP reset workaround. Weekly/before-review reset is manual; no exact-time scheduling promise.

Stop demo by suspending Render. No worker daemon is started or requires termination; request-bound mock writes are transactional. Remove demo resources to retire it, after user approval. For real worker deployment disable demo mode, use the standard deployment guide and provision suitable worker/limiter capacity separately.

## Recruiter path and limitations

Public immersive landing -> invitation login -> dashboard baseline -> Import / Use sample (or download the exact sample and upload it) -> mapping -> analyze (valid/invalid/duplicate examples) -> commit -> records -> integrations (read-only synthetic webhook, Telegram unavailable) -> deliveries (synthetic sink, no external status) -> automations (disabled) and synthetic audit trail. No real file upload encouraged; no real email signup, invite sending or Telegram connection.

Cold starts can take roughly a minute plus DB wake/migration checks; the first page can be slow. Multiple reviewers share the one synthetic workspace, so import dedupe and recent audit history are shared; they are not isolated accounts. Maximum imports needs owner reset. No continuous retry worker, timed summaries or real webhook evidence in demo. Integration count represents synthetic config, not real integrations. All data is disposable; no production SLA/backups.

## Exact post-deploy checklist

- [ ] Assigned public origin is HTTPS; HTTP redirects; certificate valid. Browser mixed-content errors absent.
- [ ] `/health/live` 200; `/health/ready` 200 and expected schema; DB shows only synthetic workspace/operator. Service refuses startup with insecure cookies, unverified DB TLS, credentials/private-webhook override or missing generated password.
- [ ] Landing and login load after real sleep; desktop/mobile immersive layout and reduced-motion fallback intact; visible banner says synthetic, sample-only and simulated deliveries. No production/worker assurance or public password appears.
- [ ] `/docs` and `/openapi.json` unavailable. HTML/API CSP, HSTS, frame denial, no-sniff present; API/auth no-store.
- [ ] Login requires preauth CSRF; wrong origin/token rejected. Session cookie Secure/HttpOnly/Lax, one-hour expiry; logout revokes it. API denied without authentication; no wildcard CORS headers.
- [ ] Generated invitation credentials work; operator cannot access/create users/admin/API keys/configure integration/test/retry/schedules. Foreign workspace/session rejected.
- [ ] First exact sample shows 2 valid / 2 invalid / 1 duplicate, commits two sample leads; subsequent import demonstrates existing-email dedupe. Mapping/analysis/report/export stay scoped. Filename normalized; modified/random CSV rejected without stored rows. Oversized and chunked bodies rejected.
- [ ] Deliveries labeled synthetic sink with no HTTP code, audit has `demo.delivery.simulated`; no real outbound request/credential access; worker_alive false, schedules disabled. No publicly callable queue/reset endpoint.
- [ ] 30-import bound and shared budget return 429; repeat/restart does not reset quota. Render no card, Free plan, no paid resources; Neon Free usage below limits.
- [ ] Restart preserves synthetic data; explicit paused offline reset invalidates old sessions and reseeds only synthetic scope. Readiness goes 503 on DB failure, errors/logs contain no credentials/input.
- [ ] Recheck billed resources, transfer/build/compute dashboards; pause if abusive. Only then record the live link and verification date.

## Local validation

See final preparation report for exact command results. Local production guard tests plus demo browser on isolated loopback test mode do not validate provider TLS, deployed Docker build, Neon connectivity, account eligibility or hosted checks on a new commit. Provider TLS, Docker startup and Neon connectivity were verified live on the deployed commit above; local tests alone do not establish those results.
