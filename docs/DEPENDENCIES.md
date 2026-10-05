# Dependency and license review · 2026-10-05

Frontend uses pnpm-lock.yaml (lockfile v9), pnpm 11.25.0 and Node 24. npm is unavailable locally and there is no npm lockfile; the applicable pnpm audit completed against the registry. Targeted compatible upgrades were performed on 2026-10-05; no broad audit fix or major upgrade.

## Advisories before and after clearance

| Package | Advisory | Audit result | Fix reported by audit |
| --- | --- | --- | --- |
| Vite 6.4.2 | GHSA-v6wh-96g9-6wx3 | moderate; Windows UNC/editor path disclosure | >=6.4.3; upgraded to 6.4.3, resolved |
| Vite 6.4.2 | GHSA-fx2h-pf6j-xcff | high; Windows development file deny bypass | >=6.4.3; upgraded to 6.4.3, resolved |
| python-dotenv 1.1.1 | PYSEC-2026-2270 / GHSA-mf9w-mj56-hr94 / CVE-2026-28684 | local env rewrite/symlink issue | 1.2.2; upgraded to 1.2.2, resolved |

Before: pnpm reported 1 high + 1 moderate. After: 0 advisories across 209 dependency entries. pip-audit requirements resolution previously covered 32 packages and returned two identical entries for one python-dotenv advisory ID: one unique advisory, not two distinct bugs. After upgrade: requirements audit covers 36 packages, zero advisories; installed environment audit covers 38 installed packages including pip 26.2, zero advisories. The application uses load_dotenv; no set_key/unset_key call was found in application or launcher source. The previous application exposure was limited; the version upgrade now closes the advisory. Vite is build/dev tooling; do not expose the vulnerable dev server publicly. Production outputs are static assets, the listed toolchain advisories are now resolved.

Primary advisory references: [Vite UNC/editor](https://github.com/advisories/GHSA-v6wh-96g9-6wx3), [Vite deny bypass](https://github.com/advisories/GHSA-fx2h-pf6j-xcff), [python-dotenv](https://github.com/advisories/GHSA-mf9w-mj56-hr94). Audit data is time-dependent; registry versions and fixes must be rechecked before an approved update. CI intentionally reports unresolved advisories as failures.

## Licenses

Installed frontend inventory contains 140 unique package/version entries: 108 MIT, 17 ISC, 6 Apache-2.0, 3 BSD-3-Clause, 2 OFL-1.1, 1 CC-BY-4.0, 1 0BSD, 1 MIT AND ISC and 1 GSAP Standard no-charge license. Inter and Manrope font notices are preserved. Three.js RoomEnvironment-derived studio reflections retain the Three.js MIT notice. caniuse-lite retains CC-BY attribution. GSAP is not MIT; its [Standard license](https://gsap.com/community/standard-license/) permits website/app use but restricts competing visual animation builder uses. This release has no visual animation builder.

Python metadata includes psycopg and psycopg-binary under LGPL-3.0-only, certifi under MPL-2.0, and other dependencies under MIT/BSD/Apache/PSF variants. Their notices have been preserved. Psycopg's [upstream license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt) and [certifi's license](https://github.com/certifi/python-certifi/blob/master/LICENSE) apply independently of a future original-code MIT license. No modified dependency source or dependency binaries are included in this source export. Any later distribution of wheels/container binaries needs a separate check of LGPL/MPL and bundled-library redistribution requirements.

Available license texts and installed-package inventories are under docs/third-party/. Python dependency metadata/license files were collected from the local virtual environment. These inventories are local evidence, not a complete legally certified SBOM or a reproducible transitive Python lock: requirements pin direct dependencies but transitive resolution can change. Verify licensing again when dependencies change.

Owner explicitly confirmed publication rights and MIT for original code/assets on 2026-10-05. MIT LICENSE and root THIRD_PARTY_NOTICES.md added. All third-party notices remain separate. See ASSET_PROVENANCE.md for included runtime assets and excluded legacy images.

## Installed Python toolchain audit

The actual virtual environment was separately audited: 38 installed packages, 14 raw advisory entries across two packages. De-duplication gives seven unique advisories: six in local pip 25.0.1 and the one python-dotenv advisory above. pip is local installation tooling, not an application runtime dependency; it is not included in the public export. pip 26.2 installed in both the existing project venv and the fresh candidate venv; pip remains absent from runtime requirements. Product dependencies and pip check pass.

| Package | Advisory | Fix reported |
| --- | --- | --- |
| pip 25.0.1 | PYSEC-2026-1795 / GHSA-4xh5-x5gv-qwph | 25.3 |
| pip 25.0.1 | PYSEC-2026-1796 / GHSA-6vgw-5pg2-w6jp | 26.0 |
| pip 25.0.1 | PYSEC-2026-2875 / GHSA-58qw-9mgm-455v | 26.1 |
| pip 25.0.1 | PYSEC-2026-2876 / GHSA-jp4c-xjxw-mgf9 | 26.1 |
| pip 25.0.1 | PYSEC-2026-196 / GHSA-wf93-45jw-7689 | 26.1.2 |
| pip 25.0.1 | PYSEC-2026-3721 / GHSA-qwm4-qh6w-59xr | 26.2 |

## Clearance outcome

Vite 6.4.3 is the minimum patched release in the existing 6.x line for both listed advisories. Only the Vite pin and its lockfile references changed; the other 139 frontend package versions were preserved. python-dotenv 1.2.2 is the first patched release; application load_dotenv usage stays compatible and full tests validate it. pip 26.2 covers all six listed installer advisories. npm is unavailable and package-lock.json is absent: npm audit SKIP; pnpm audit is the authoritative frontend check. Python tooling audit environment is separate from product requirements.

Fresh transitive Python resolution differs from historical inventory (36 resolved requirement audit packages); direct runtime pins remain unchanged except dotenv. Audits certify known advisories at run time, not absence of all vulnerabilities. Python transitive dependencies are not hash-locked.

Explicit installer audit: freeze --all includes pip; both main project and candidate environments have 38 installed packages and zero advisories. Frontend inventory comparison confirms only Vite changed version (6.4.2 to 6.4.3).
