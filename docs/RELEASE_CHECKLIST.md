# Release/rollback checklist · 0.5.0-rc.1

## Candidate acceptance

- [x] Canonical folder, PostgreSQL/Auth/RBAC/EN/UA/RU/M4 baseline verified.
- [x] No new product features/integrations, deploy or publication.
- [x] Production guards, cookies/CSRF/origin, headers/docs gating/upload limits.
- [x] Import/outbox/retry/fencing/process-fault regression; current docs/verification.md evidence.
- [x] Disposable test-data backup/restore, never overwriting runtime.
- [x] Three languages/four widths, keyboard/focus/dialog/labels/targeted contrast.
- [x] Topology/migration/retention/alerts/docs/public-safe case study.
- [ ] Actual production edge TLS/HSTS/proxy/shared limits and restricted DB.
- [ ] Docker Compose runtime startup/worker/volume-restart smoke.
- [ ] Real provider credentials/delivery approved and independently tested.
- [ ] Encrypted off-host backup/restore roles, RPO/RTO and alert owners.
- [x] Dependency/license clearance completed; targeted upgrades and clean audits recorded in DEPENDENCIES.md.
- [x] Listed dependency advisories resolved; fresh audits show zero known vulnerabilities.
- [x] Desktop Chrome and owner-reported iPhone Safari real-device PASS.
- [ ] Physical Android Chrome QA.
- [x] Owner confirmed original asset rights and approved MIT; LICENSE and THIRD_PARTY_NOTICES added.
- [ ] Execute GitHub-hosted CI after approved repository creation.
- [ ] Public staged-file/history/privacy review and publication approval.

## Deployment after approval

Record immutable version/hashes and previous known-good build. Provision isolated synthetic demo/accounts, private credentials and restricted DB roles. Backup/restore test. Drain workers/freeze mutations, migrate once, API readiness, worker fleet, frontend/HTTPS. Test auth/RBAC/import/outbox/delivery/cookies/headers/queue age before opening traffic. Record operator/time/evidence privately. No internal operational IDs or endpoints in public materials.

## Rollback

1. Freeze public writes, stop/drain workers; preserve durable queue.
2. Preserve redacted diagnostics, take private DB backup; record revisions.
3. Prefer compatible prior app with current DB. M5 adds only worker_heartbeats, but M4 readiness checks exact old revision: rolling API back without schema plan fails.
4. Rehearse alembic downgrade a4outbox000001 on restored DB first. Drops idle pulse data, not import/outbox. Never downgrade M4/M3 production without data-loss review.
5. If restore required, restore NEW isolated DB, verify counts/checksums/roles, switch config under freeze; preserve original. Post-backup writes lost; sent messages cannot be undone.
6. Start chosen API/worker/frontend, verify readiness/auth/import state/queue/fencing/receiver dedupe. At-least-once repeated remote effects expected around interrupted work.
7. Reopen after smoke, record replay/data gap and adjust alerts. Never promise exactly-once or zero restore loss.
