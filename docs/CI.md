# Release candidate CI

.github/workflows/ci.yml is prepared for pull requests and pushes with read-only repository permissions. It does not deploy, publish packages or push tags.

The verification job uses PostgreSQL 16 with an isolated astrasynq_test database and public synthetic CI-only credentials. It runs backend pytest, TypeScript, production build, packaging, application browser regression, portable reduced-motion/unavailable-WebGL/save-data smoke, release-static checks and public-file checks. Python 3.12, Node 24 and the frontend pnpm lockfile are used. Browser seeding generates ephemeral passwords rather than committing a reusable account.

scripts/ci-browser.py starts and stops only its own API/frontend processes. Test artifacts and logs stay private; CI does not upload them. Browser seeding supports both Windows and Linux. The separate advisory job runs pip-audit and pnpm audit and intentionally fails on unresolved advisories; it has no allowlist hiding known issues.

Full immersive, landing-handoff and performance-gate functional browser suites run locally using installed Chrome. GPU cadence, adaptive rendering, touch, orientation and device heat are hardware-sensitive and are not asserted by the portable CI smoke job. Physical iPhone QA comes from the owner; physical Android remains unverified. Heavy performance benchmark campaigns were not repeated during preparation.

GitHub-hosted Linux execution is pending. Local Windows equivalent execution validates the portable launcher and smoke checks, but does not certify the hosted workflow itself. Docker runtime is also pending.

Clearance: YAML parses successfully and uses only synthetic test credentials/PostgreSQL 16; no secrets references. Installer pip is pinned to 26.2 in the verification environment. Browser install uses the explicit Playwright CLI. Full local test defaults write only generated ignored .clearance artifacts. Hosted Linux and Docker runtime remain unexecuted. Portable smoke sets ASTRASYNQ_PORTABLE_SMOKE=1 and skips the GPU transition inside the reduced-motion case. Full local immersive suite retains this transition assertion. The three hosted landing smoke checks do not require a GPU.
