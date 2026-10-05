# Automation architecture and operations

Migration `a4outbox000001` follows `a3auth0000001`; upgrade creates five tables; downgrade drops schedules, jobs, deliveries, integration_configs, events in dependency order. DDL is frozen in the migration and exported in automation-schema.sql. Downgrade destroys automation history; it leaves M3 tables in place.

## Durable event flow

Import commit already locks workspace/import rows. Inside the same PostgreSQL transaction, it stores the completed import, leads, an event and recipient delivery/jobs. Unique `events.dedupe_key=import:<import UUID>` prevents duplicate events. Event UUID is generated once and remains unchanged through retry and restart. If any operation fails, the transaction rolls back all these writes. Completed legacy M3 imports are not replayed automatically.

At commit, enabled integrations become recipients. Each has exactly one delivery per event through the unique `(event_id,integration_id)` key. Each delivery has one persistent job. A completed routing job records outbox routing even with zero recipients; it represents routing inside the commit transaction, not a second asynchronous fanout step. Later enablement does not replay old imports.

The standalone Python worker polls PostgreSQL, using `FOR UPDATE SKIP LOCKED` to claim one ready queued/retry or expired running job. It increments attempts, assigns a fresh lease UUID, commits the claim, then performs HTTP outside that transaction. Lease is 60 seconds; heartbeat renews every 10 seconds. Final writes require the same token and an unexpired lease. An old worker cannot overwrite a new owner's result. Abrupt termination leaves the durable job; another worker recovers it after lease expiry.

Success completes job/delivery. Failure schedules exponential backoff `min(86400, backoff * 2^(attempt-1))`. Timeout 1–20 seconds, attempt budget 1–10, base backoff 1–3600 seconds. Every claim, including crash recovery, consumes an attempt. Exhaustion is terminal with a secret-free worker audit entry. Delivery attempts count lifetime claims; manual retry resets the job's per-run budget but keeps lifetime delivery attempts and event ID. Manual retries are only allowed on failed/paused jobs while integration is enabled. Disabling a connection pauses ordinary jobs; re-enable and manually retry paused jobs. Test events explicitly work with disabled saved configurations.

Semantics are **at-least-once**: a receiver may accept HTTP before the worker crashes or loses its lease. The subsequent recovery can resend the same event. Receivers must deduplicate on event_id; local records and fencing cannot guarantee exactly-once effects in a remote service. Destination/policy/credential reference are read from the current saved configuration at execution time, while recipient selection is captured at commit. Changing destination can therefore route an existing retry to the new destination.

## Schema

- events: UUID, workspace FK, type, unique dedupe_key, JSONB payload (IDs/counts/status only), created_at.
- integration_configs: UUID, workspace FK, unique workspace/kind, enabled, destination, credential_ref, timeout, max_attempts, backoff, updated_at; kind/policy checks.
- deliveries: UUID, workspace FK, event/config FKs, unique event/config, status, lifetime attempts, last safe error code, response_code, created/updated/delivered times.
- jobs: UUID, event/delivery FKs, unique dedupe_key/delivery_id, status, attempts/max_attempts/backoff, run_after, lease_until, heartbeat_at, lease_token, created_at; queue index/checks.
- schedules: UUID, unique workspace FK, enabled, IANA timezone, next_run_at, updated_at.

## Credentials and outbound security

The UI accepts only names matching `ASTRASYNQ_CREDENTIAL_[A-Z0-9_]+`, never raw tokens/secrets. Store values privately in worker environment (or an ignored local .env). Database/audit/OpenAPI hold no secret value; the UI displays a fixed mask. API does not test presence of env values; worker reports credential_missing safely. Audit stores actor/action/entity IDs only. Response bodies and exception text are not persisted/logged because they may expose tokens or personal data. Local launcher and worker logs contain no credential-bearing URL. Runtime secrets are not requested in tests or committed.

Tradeoff: credentials require operator environment provisioning and a worker restart on rotation. No DB encryption key is needed because the DB stores references only. The browser cannot upload a real bot token or HMAC secret. A central secret manager/encrypted per-workspace credentials can be added later. Use a strong webhook secret (at least 32 random bytes recommended). Environment and local .env protection remain host/operator responsibilities.

Webhook sends exact compact sorted JSON containing event_id, type, time, data. Headers:

- X-AstraSynq-Event-ID: stable UUID
- X-AstraSynq-Timestamp: fresh Unix timestamp per attempt
- X-AstraSynq-Signature: `sha256=<hex HMAC-SHA256(secret, timestamp + '.' + event_id + '.' + raw_body)>`

Receiver verifies the raw bytes using constant-time comparison, rejects stale timestamps (e.g. over five minutes), checks body/header IDs match and deduplicates by event_id. Retries reuse ID/body event time but refresh the signing timestamp. Webhook 2xx is delivered; all other status codes, including 4xx/5xx/redirects, retry under bounded policy; timeout/transport failures retry. No raw receiver response is displayed, only HTTP status and safe error category.

Production requires HTTPS; rejects userinfo, query strings, fragments and any DNS answer that is not globally routable (including IPv4/IPv6 loopback, private, link-local, metadata, reserved). Validation occurs on configuration and again on every delivery. Transport connects to a validated IP while retaining hostname TLS verification/SNI; redirects and environment proxies are not followed. Development permits HTTP/private destinations only when BOTH `ASTRASYNQ_MODE=development` and `ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS=true` are explicitly set. Production overrides the private flag. DNS lookup uses the platform resolver; its own wall-clock timeout is not controlled by socket HTTP timeout. Add outbound network restrictions in deployment as defense in depth.

Telegram only sends to the fixed api.telegram.org Bot API sendMessage endpoint. Chat ID must be numeric; bot token comes from the configured env reference and is format-checked. HTTP 2xx plus `ok:true` is delivered; rejected/non-2xx/timeout retries. Message includes import ID, counts, status and event time; no names/emails/raw source records. Token never appears in response history.

## Daily summary

One MVP schedule per workspace at 09:00 in selected IANA timezone, with DST-aware next-run computation. Worker locks due schedules using SKIP LOCKED, persists `summary.daily` and jobs, and advances next_run_at in one transaction. The summary covers completed imports in the 24 hours ending at the scheduled due time. If worker is offline across several days, it creates one overdue summary then schedules the next future run; it does not flood recipients with every missed day. Daily calendar-day reporting, per-user language for Telegram, catch-up modes, arbitrary cron/recurrence and multiple schedules are future work.

## RBAC and audit

Viewer: read integrations (reference + fixed mask), delivery history, schedules, metrics and workspace jobs. Operator: these reads, queue tests to saved destinations, retry eligible failed/paused deliveries. Admin: all plus configuration/enable-disable and schedule management. All permissions, CSRF and workspace scope are checked on the server. Viewer UI has no mutation actions; operator cannot edit destinations or references. Tests have a pending-delivery cap per integration to limit accidental queue flooding; this is not a distributed time-window abuse limiter.

Audit actions: integration.changed, delivery.test, delivery.retry, schedule.changed, delivery.failed. Actor is absent for worker failures. Dashboard reads enabled integration counts, delivered/failed/pending totals, active schedules and last claim/heartbeat from DB. Last worker activity is historical, not a live process liveness guarantee during idle time.

## Verification / future hardening

Tests use real PostgreSQL astrasynq_test, HTTP boundary mocks for Telegram and ordinary webhook outcomes, and an actual separate worker process with a loopback HTTP webhook. No real external delivery is part of QA. Leases, fencing, competing claims, rollback/idempotency, exponential retries, terminal failure, restart persistence, schedule/DST, HMAC, SSRF and manual retry are covered. Browser checks cover all three languages, new pages, roles and mobile/tablet/desktop widths.

M5: wider concurrency/load/fault testing, production egress controls and secret manager, shared rate limits, worker health/alerts and metrics, queue/history retention, accessibility/final QA, deploy plan and portfolio material. Deployment itself requires a separate user request. Single-message worker concurrency is intentional; scale by adding worker processes. Telegram has no remote idempotency key, so duplicate notifications remain possible under at-least-once delivery. Retry-after/jitter/circuit breaker and destination snapshots are not implemented.
