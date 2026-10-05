# Authentication and authorization · 0.5.0-rc.1

Users authenticate with Argon2id password verification. Opaque session tokens are stored as hashes in PostgreSQL; cookies are HttpOnly. Session revocation, user deactivation and role changes are enforced server-side. There is no default administrator or shared runtime password.

Bootstrap the first admin from backend with `python -m app.bootstrap_admin`; credentials are entered privately. Do not place real bootstrap values in docs or shell history. Browser QA creates disposable example.test users and an ephemeral generated password in the isolated astrasynq_test database only.

Viewer can read workspace data. Operator can import/export and test/retry deliveries. Admin also manages users, integration configuration and schedules. API requests derive workspace membership from the authenticated user; cross-workspace resources do not reveal their existence.

Pre-auth CSRF uses a double-submit token; authenticated mutations use per-session CSRF. Origin and Fetch-Site checks reject cross-site access. Production requires Secure cookies, HTTPS and exact trusted origins. Same-origin deployment does not enable wildcard credentialed CORS.

The process-local login limiter is bounded and does not trust arbitrary forwarding headers. Shared ingress rate limits and a trusted client-IP policy must be configured for production. It is not distributed across API processes.

Normalized-email uniqueness and cross-workspace duplicate detection follow the current single-workspace product policy. This release does not establish a tenant-isolated SaaS deduplication policy. Secrets, session/cookie dumps and runtime user records stay private.

See SECURITY.md, DEPLOYMENT.md and the generated openapi.json for current contracts and environment limitations.
