# Changelog

## v0.5.0-rc.1 — draft, untagged

Local Release Candidate for AstraSynq, a Data Automation & Integration Platform. This draft does not represent a deployment or published release.

- PostgreSQL persistence, SQLAlchemy models and Alembic migrations.
- CSV upload, mapping, validation, duplicate review and atomic idempotent import commit.
- Session authentication, CSRF protection, Argon2id and Viewer/Operator/Admin RBAC.
- Transactional outbox, leased worker, fenced writes, retries, delivery history and audit.
- HMAC webhook delivery, Telegram integration and timezone schedules.
- EN/UA/RU workspace and immersive WebGL landing with reduced-motion/failure fallback.
- Public-safe documentation, curated synthetic screenshots and draft GitHub Actions checks.

Device evidence: desktop Chrome PASS; iPhone 14 Pro Max / Safari real-device PASS per owner; physical Android Chrome UNVERIFIED. Exact current verification is in docs/verification.md.

Known limitations: physical Android and Docker runtime pending; production TLS/proxy, database SCRAM/permissions, egress controls, secret manager, shared rate limiting and deployment/restore drills require validation. At-least-once delivery can repeat remote effects. Large WebGL chunk warning remains. Dependency advisories remain open; see docs/DEPENDENCIES.md. Hosted CI has not yet executed. Project-wide licensing awaits owner confirmation of original assets.

No tag, commit, push, GitHub repository, live demo or deployment has been created during preparation.
