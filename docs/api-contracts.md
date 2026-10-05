# AstraSynq API � 0.5.0-rc.1

OpenAPI: docs/openapi.json, release version 0.5.0-rc.1. Swagger is development-only at your local API /docs route. Data routes require an active server session and membership. Workspace is server-derived; no demo UUID/header access. 401 means no valid active session; 403 means role/CSRF rejection; cross-workspace entities return 404. Auth/user/audit contracts and Swagger steps: [authentication](authentication.md).

| Route | Behavior |
| --- | --- |
| GET /health/live | Process liveness. |
| GET /health/ready | PostgreSQL + expected Alembic revision; 503 unavailable/unmigrated. |
| POST /api/v1/imports | Multipart CSV <= 5 MiB/10,000 rows; persist raw rows; 201 ImportResult. |
| GET /api/v1/imports | ImportPage items,total,page,page_size; optional uploaded/mapped/analyzed/completed status, literal case-insensitive filename search. |
| GET /api/v1/imports/{id} | Saved mapping, classifications and field/code issues. |
| PUT /api/v1/imports/{id}/mapping | Canonical fields → existing columns; email required, no column reused. Status mapped; clears analysis/issues. |
| POST /api/v1/imports/{id}/analyze | Persistent analysis; analyzed means ready for review. |
| POST /api/v1/imports/{id}/commit | Atomic/idempotent, import_id/inserted/status=completed. Stale review/late unique conflict → 409 workspace_changed with refreshed review saved; re-read/review before retry. |
| GET /api/v1/imports/{id}/issues.csv | Saved issues; requires analyzed/completed, otherwise 409 report_first. |
| GET /api/v1/leads | LeadPage items,total,page,page_size; optional literal email/name search, exact company, UUID import_id. Items: id,import_id,email_normalized,created_at,data. |
| GET /api/v1/leads/export.csv | All matching DB leads; same search/company/import_id filters. |
| GET /api/v1/dashboard/summary | Completed-import aggregates, actual lead count, 14 UTC insertion-date buckets, 20 latest completed imports/10 leads; mode postgresql. |
| GET /api/v1/samples/leads.csv | Original 12-row sample. Fresh seed 8 valid/2 invalid/2 duplicates; after commit repeated file 0/2/10. |

Pagination: page >= 1, page_size 1..100, default 1/20. Lists/export sort created_at DESC,id DESC. Per-request count/list snapshot is consistent. Dashboard counts completed imports; list includes drafts. Search escapes SQL wildcard characters. CSV cells whose stripped value starts with =,+,-,@ receive an apostrophe prefix.

Validation issues stay language-neutral field/code. Six validation codes and lifecycle errors translate through EN/UA/RU. Completed imports cannot be remapped/reanalyzed. CSV dates normalize to UTC; naive dates assumed UTC. Custom workspaces are not auto-seeded.

Auth is implemented. Integration writes remain Admin-only 501 contracts; jobs remain authenticated 501 contracts. Read placeholders exist for integrations and Admin API keys. No worker/external delivery added. See authentication.md for the complete RBAC matrix.

## Automation APIs

The former integrations/jobs contract placeholders are implemented. GET /integrations returns scoped masked configuration; PUT /integrations/{webhook|telegram} accepts destination, credential_ref, enabled, timeout, max_attempts, backoff. POST /integrations/{kind}/test queues a persistent test event (202). GET /deliveries paginates delivery history; POST /deliveries/{uuid}/retry queues an eligible retry (202). GET /automations and PUT /automations/daily-summary read/manage enabled/timezone/next_run_at. GET /automation-metrics exposes real DB totals; GET /jobs/{uuid} exposes workspace-scoped job status/lease/retry state. See generated openapi.json and automation.md. All mutations require session CSRF, and server RBAC is mandatory.
