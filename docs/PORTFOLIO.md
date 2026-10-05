# Portfolio / case study draft

AstraSynq is a Data Automation & Integration Platform built with FastAPI, React, TypeScript and PostgreSQL. It turns inconsistent CSV files into validated, deduplicated records and durable automation events. A guided import explains errors before commit; EN/UA/RU dashboards show data quality and delivery history.

The reliability design combines atomic import/outbox transactions, idempotent commit, worker leases, fenced writes and durable retries. Signed webhooks and Telegram summaries use at-least-once delivery; receivers should deduplicate stable event IDs. Auth/RBAC, CSRF, upload bounds, validated outbound connections and security headers protect the application boundary.

An original procedural board/chip WebGL landing introduces the same import lifecycle, with semantic content, adaptive rendering and reduced-motion/failure fallbacks. Curated synthetic screenshots are in docs/screenshots/.

Release state: 0.5.0-rc.1, Local Release Candidate. Exact current verification: docs/verification.md. Desktop Chrome and owner-reported iPhone 14 Pro Max Safari real-device QA PASS; physical Android pending. Docker runtime and production environment validation are pending. No claim of production readiness, proven production usage or live deployment is made.

This text is a local draft. No portfolio account updates, hosted demo or public repository were performed. Dependency advisories and asset/license decisions must be resolved/reviewed before approved publication.
