# Dependency + License Clearance verification · 2026-10-05

Candidate: public-candidate-final; version 0.5.0-rc.1. All results below were executed again after targeted upgrades; historical counts are not substituted. No publishing/tag/deploy or product feature changes.

| Verification | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Backend / actual isolated PostgreSQL | 154 | 0 | 0 |
| Application browser regression / fresh Playwright Chromium | 22 | 0 | 0 |
| Full immersive / UI | 26 | 0 | 0 |
| Reload / handoff matrix | 1 | 0 | 0 |
| Functional quality | 14 | 0 | 0 |
| Packaging | 4 | 0 | 0 |
| Release static | 5 | 0 | 0 |
| **Primary suite total** | **226** | **0** | **0** |

TypeScript PASS; production build PASS, 2966 modules transformed. Fresh backend venv + pip check PASS. Frozen-lockfile frontend install PASS: 140 packages downloaded into a new candidate-local store without reusing parent dependencies. Python runtime/test requirements audit PASS: 36 resolved packages, 0 advisories. Installed candidate venv audit PASS: 38 installed package entries including pip 26.2, 0 advisories. Frontend pnpm audit PASS: 209 dependency entries, 0 advisories. npm audit SKIP: npm unavailable and no npm lockfile.

Fresh dedicated PostgreSQL database migrations and README start-local/stop-local PASS: API readiness reports PostgreSQL/0.5.0-rc.1, frontend returns HTTP 200; API/frontend/worker started and stopped. No .env file exists or was required. Existing loopback PostgreSQL service was used without reading its private data directories; database provisioning download/runtime not repeated. The README requires a PostgreSQL service or the optional documented provisioner. The new synthetic clearance database was separate from runtime and test databases.

CI YAML parse and synthetic environment/topology checks PASS. Hosted Linux workflow execution and Docker runtime SKIP (not performed). Portable CI browser results are recorded below separately; repeated app coverage is not included in the 226 total. Full visual GPU assertions remain local; hosted smoke disables the reduced-motion GPU transition.

Warnings: 1 Starlette TestClient/httpx deprecation warning in pytest; WebGL minified chunk 1257.68 kB exceeds 500 kB. pip version-check network warning appeared during installation; explicit package installs, pip check and advisory queries succeeded. Python transitive dependencies are not hash-locked. Hardware benchmark campaigns and physical Android QA SKIP. Real iPhone PASS remains owner-reported historical evidence, not re-executed in this clearance.

Owner confirmed original code/assets publication rights and MIT in this clearance session. LICENSE, THIRD_PARTY_NOTICES.md and per-file asset inventory added. No unconfirmed legacy imagery is included. Third-party components retain upstream licenses; later binary/container redistribution requires its own LGPL/MPL/bundled-library review.

Final public-file/privacy results and manifest are recorded below after the final documentation edits. Generated venv, dependencies, dist, logs, screenshots and audit caches are ignored and excluded from the public manifest. Never upload the entire candidate directory as an archive without applying the public selection.

Portable CI-equivalent browser launcher: app 22 PASS / 0 FAIL / 0 SKIP; deterministic landing smoke 3 PASS / 0 FAIL / 0 SKIP. These are repeated checks outside the primary 226 total. Smoke selected only the three named cases; other full immersive cases were not scheduled in this run.

Final public safety: PASS, 360 selected public files, zero blocking secret/privacy matches, zero unexpected files outside ignored generated trees. No real .env, DB dumps, logs, HAR, cookies/session exports, personal absolute paths/usernames or real chat IDs/tokens in the public set. Two private-IP literals are explicit SSRF-denial test fixtures, not local network configuration. Synthetic CI password and test-only authentication values are deliberately public fixtures. Six screenshot PNGs have no embedded metadata and show synthetic test accounts; third-party copyright identities belong to license attribution and are retained. Largest public file is hero.png: 1,176,628 bytes; zero files exceed 25 MB.

Readiness: READY for a clean public source repository after separate owner confirmation. Hosted CI/Docker/device gaps above are explicit limitations, not deployment certification. Next authorized publication procedure: create a new empty GitHub repository with the owner-approved name; initialize fresh history from only the manifest-selected public files, inspect the staged list for ignored/generated data, commit and push main, wait for both hosted CI jobs to pass, then create and push annotated v0.5.0-rc.1. Do not import the private working tree or old history. None of these publication steps was performed.

Explicit installer audit: freeze --all includes pip; both main project and candidate environments have 38 installed packages and zero advisories. Frontend inventory comparison confirms only Vite changed version (6.4.2 to 6.4.3).
