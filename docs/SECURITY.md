# Security hardening · 0.5.0-rc.1

Local evidence-based review, not full independent penetration test/compliance certification.

## Fixed findings

1. Unsafe production auth defaults: reject non-Secure cookies, non-HTTPS/wildcard/path origins, weak/missing DB credentials, bad mode/SameSite/private-webhook override; never echo values.
2. Multipart spool before size check: pre-parser ASGI 6 MiB bound including chunked bodies. CSV 5 MiB, extension/MIME, UTF-8/BOM/strict structure, 30 columns/10,000 rows; file close on rejection.
3. Partial headers: API/frontend CSP, nosniff/referrer/frame protection. HSTS HTTPS/prod-only with edge requirements.
4. Dev docs exposure: production docs/redoc/OpenAPI unavailable. No auth-bypass/debug admin endpoint found. Errors safe codes, no request/exception echo.
5. Logging: generated request IDs/allowlisted JSON; raw access logs disabled in launcher/image; never SQL/HTTP debug in production.
6. Compose lacked worker/seeded demo automatically: explicit worker/migration topology, no image seed, non-root backend, env excluded from image contexts.
7. Disabled integration pause now checks lease expiry/running state/token before write; stale fencing preserved.

## Auth/CORS/CSRF

Opaque sessions need no shared SECRET_KEY: token hashes in DB, CSRF from unpredictable session token. No placeholder encryption/signing key added. Argon2id, last admin protection, role-change session revocation. Cookies HttpOnly, lax/strict, Secure production. Preauth double-submit and per-session CSRF use constant-time checks. Origin/Fetch-Site reject cross-site. CLI still needs cookies/tokens. Same-origin deployment intentionally has no CORS; never wildcard credentialed CORS.

Login limiter **process-local**, 10 attempts/IP/minute, 1024 IP memory bound, no arbitrary forwarded headers. Defense in depth, not distributed protection; public multiple processes require shared edge login/API limits and trusted real-client-IP policy. No SaaS/distributed limiter added.

Audit covers login success/failure/logout, import analyze/commit, exports, users/roles, integration/schedule changes, tests/retries/terminal failure. No payload/secrets. Unknown-user failure unscoped; anonymous 403/429 operational logs rather than workspace audit.

## Outbound/secrets

Production HTTPS; no URL credentials/query/fragment; reject any non-global DNS including mixed public/private, IPv6/mapped loopback/metadata/shared ranges. Revalidate per send; connect pinned validated IP with verified host TLS/SNI; no redirects/env proxy. Rebinding regression verifies second resolution cannot replace pinned IP. HMAC covers timestamp + '.' + event_id + '.' + exact bytes; receiver verifies freshness/HMAC/dedupe.

Limitations: OS DNS has no app wall-clock deadline; socket inactivity timeout is not whole-response deadline for slow drip; read capped 65,536 bytes. Production needs egress/DNS/time policies. No new secret SDK/encryption scheme/Retry-After/jitter/circuit breaker. Telegram 429 uses exponential retry, tune for volume.

Real values only private worker env; UI/DB references only, rotation restarts worker. Compose credential values only worker. No committed real env/tokens/passwords/keys/dumps/sessions/logs/screenshots. Public contracts/tests/examples synthetic. Source pattern scan and response/error regression cannot prove every secret absent; staged-file/history review before publishing.

## Database/production gates

Local loopback trust cluster **dev-only**. Production SCRAM/private network/least privilege runtime vs migration roles, remote verify-full TLS, encrypted backups/role review. URI validation cannot check actual pg_hba/grants. Compose bootstrap superuser must be replaced by restricted runtime role in production config.

Remaining: real HTTPS edge/HSTS/CSP/proxy/limits, shared login/API protection, egress/DNS, restricted DB, encrypted off-host restore/roles, synthetic isolated demo, dependency advisory/network review, actual Docker smoke. No real external messages used. Gates documented, not completed claims.
