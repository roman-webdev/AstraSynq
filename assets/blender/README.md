# Astra Core — authored Blender asset

Original AstraSynq geometry and procedural surface maps; no external branded
models, textures, photos or videos. Blender executable is installed separately
at `<blender-executable>`.

`astra-core.blend` contains the editable assembly, original materials, packed
micro-normal/roughness maps, Cycles studio lights, camera and render-only routes.
`build_core.py` reconstructs the model and exports selected geometry as glTF.
`board-layout.json` records the existing ReferenceBoard route/component layout,
so the browser's animated traces continue to match the processor and pads.
`pack_model.py` creates a standard source GLB and compresses its geometry for
the browser, keeping WebP texture URLs external. No runtime Blender dependency.

Rebuild from the project root:

```powershell
& '<blender-executable>' --background --factory-startup --python assets\blender\build_core.py
.venv\Scripts\python.exe assets\blender\pack_model.py
```

Geometry uses the same XY board / Z-up coordinates as CoreAssembly, intentionally
exported with `export_yup=False`. This is an internal Three.js asset convention;
general glTF viewers expecting Y-up may need a 90-degree presentation rotation.
Rendering merges static parts by material (14 meshes) and retains dynamic traces
in Three.js. No lights or camera are baked into the exported model.

The browser scene uses native gzip decompression, avoiding blob workers / WASM
decoders and preserving the existing CSP. The browser materials use baked normal
and roughness maps, environment reflections and one physical shadow light.

Offline Cycles reference previews are optional generated development artifacts and are not included or required for runtime/build.
