# Asset provenance and license review

| Asset group | Local evidence | Public decision |
| --- | --- | --- |
| Attached board/chip geometry and ceramic/PCB maps | assets/blender/build_core.py, board-layout.json and manifest.json declare original procedural authoring | Runtime compressed model/maps included; Owner confirmed publication rights and MIT on 2026-10-05 |
| Animated board geometry | frontend/scripts/build-board-geometry.mjs generates the runtime buffers | Include generator and runtime buffers |
| Studio reflection environment | frontend/scripts/bake-studio.mjs uses Three.js RoomEnvironment, not a downloaded HDR photo | Include runtime buffer; preserve Three.js MIT notice |
| Current fallback posters | frontend/scripts/capture-core-poster.mjs captures the local scene | Include current posters; Owner confirmed provenance on 2026-10-05 |
| Older photographic plates / chip-top / material images | Legacy files lack a complete per-file rights trail in this folder | Exclude from curated export; unused legacy CoreBoard/CoreProcessor components are also excluded |
| Blender editable file, raw GLB/glTF and backups | Original-author declaration; unnecessary for runtime | Keep local in first public candidate; include reproducible authoring scripts |
| Inter and Manrope fonts | Installed @fontsource package licenses are SIL OFL 1.1 | Include font notices; do not relicense as MIT |
| GSAP | Standard no-charge license, distinct from MIT | Preserve terms; current app is a data platform, not a visual animation builder |
| README screenshots | Fresh synthetic browser test captures / local scene captures | Reviewed curated subset only; no browser address bars or runtime accounts |
| Sony/PS5/stock/video design references | Inspiration recorded in internal design history | References and original media are not exported |

The owner explicitly confirmed rights to original code, procedural Blender assets, scene posters and synthetic application screenshots on 2026-10-05 and authorized MIT. LICENSE now applies to those original contributions. Third-party components retain their licenses in THIRD_PARTY_NOTICES.md. Per-file public inventory with SHA-256 values: docs/third-party/asset-inventory.json. No unconfirmed legacy photographic assets are included. Authorship is supported by the included procedural generators and owner declaration; historical execution is not independently reconstructed.

A mobile iPhone screenshot is explicitly marked iPhone viewport emulation in Chromium. No real iPhone screenshot or recording was supplied for this preparation; the real-device PASS statement is owner-reported.
