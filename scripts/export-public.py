"""Export an explicit curated candidate inside the project; never commit/publish."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_checks',ROOT/'scripts/check-public-files.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
p=argparse.ArgumentParser();p.add_argument('--output',default='work/public-release/public-candidate');args=p.parse_args()
target=(ROOT/args.output).resolve()
if target==ROOT or ROOT not in target.parents or target.parts[len(ROOT.parts)]!='work':raise SystemExit('Export must stay under project work/')
if target.exists() and any(target.iterdir()):raise SystemExit('Export destination must be empty; use a new candidate directory')
files=sorted(checks.public_files());issues=checks.inspect(files)
if issues:
    for rel,kind in issues:print(kind+': '+rel)
    raise SystemExit('Candidate privacy checks failed')
manifest=[]
for source in files:
    rel=source.relative_to(ROOT);dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    manifest.append({'path':rel.as_posix(),'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
(target/'PUBLIC_FILE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Curated candidate exported: {len(files)} files; {sum(x["bytes"] for x in manifest)} bytes; no Git operations')
