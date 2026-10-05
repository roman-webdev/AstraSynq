"""Read-only public candidate selection and privacy checks; no Git operations."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
PUBLIC_DOCS={'api-contracts.md','architecture.md','auth-schema.sql','authentication.md','automation-schema.sql','automation.md','DEPLOYMENT.md','SECURITY.md','RELEASE_CHECKLIST.md','openapi.json','PORTFOLIO.md','PUBLIC_RELEASE.md','ASSET_PROVENANCE.md','DEPENDENCIES.md','CI.md','verification.md'}
PRIVATE_PARTS={'.git','.venv','.local','.pnpm-store','node_modules','dist','work','previews','__pycache__','.pytest_cache','test-results','playwright-report','coverage','.clearance'}
ROOT_FILES={'.env.example','.gitignore','README.md','CHANGELOG.md','compose.yaml','LICENSE','THIRD_PARTY_NOTICES.md','PUBLIC_FILE_MANIFEST.json'}
BLENDER_FILES={'README.md','build_core.py','pack_model.py','board-layout.json','manifest.json'}
VISUAL_FILES={'astra-board-desktop.bin','astra-board-mobile.bin','astra-ceramic_normal.webp','astra-ceramic_roughness.webp','astra-core.model.bin','astra-pcb_normal.webp','astra-pcb_roughness.webp','astra-studio.bin','core-poster-desktop.webp','core-poster-mobile.webp'}
DENIED_SUFFIXES={'.log','.db','.sqlite','.sqlite3','.dump','.backup','.bak','.blend1','.har','.webm','.mp4','.pem','.key','.p12','.zip','.7z','.pyc','.pyo'}
PATTERNS={'provider credential':r'(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|\b\d{6,20}:[A-Za-z0-9_-]{30,}\b)','private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','personal absolute path':r'(?:[A-Za-z]:[\\/]Users[\\/][^\s]+|/home/[^/\s]+/)'}
def selected(path):
    rel=path.relative_to(ROOT);parts=rel.parts
    if path.is_symlink() or any(p in PRIVATE_PARTS for p in parts):return False
    if path.suffix.lower() in DENIED_SUFFIXES:return False
    if path.name.startswith('.env') and rel.as_posix()!='.env.example':return False
    if len(parts)==1:return rel.as_posix() in ROOT_FILES
    if parts[0]=='docs':return (len(parts)==2 and parts[1] in PUBLIC_DOCS) or parts[1] in {'screenshots','third-party'}
    if parts[:2]==('assets','blender'):return len(parts)==3 and parts[2] in BLENDER_FILES
    if parts[0]=='.github':return parts[1]=='workflows' and path.suffix in {'.yml','.yaml'}
    if parts[0] not in {'backend','frontend','scripts'}:return False
    if parts[:3]==('frontend','public','visuals'):return len(parts)==4 and parts[3] in VISUAL_FILES
    if path.name=='AGENTS.md':return False
    if rel.as_posix() in {'frontend/src/immersive/CoreBoard.tsx','frontend/src/immersive/CoreProcessor.tsx'}:return False
    return True

def public_files():
    # Prune private trees; never recursively enter PostgreSQL data or dependency stores.
    import os
    for base,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in PRIVATE_PARTS]
        for name in names:
            p=Path(base)/name
            if selected(p):yield p

def inspect(paths):
    issues=[]
    for p in paths:
        rel=p.relative_to(ROOT).as_posix()
        if p.stat().st_size>25_000_000:issues.append((rel,'large file requires review'))
        raw=p.read_bytes()
        if b'\0' in raw[:8192]:continue
        text=raw.decode('utf-8',errors='replace')
        # Pattern definitions are not leaked credentials.
        if rel=='scripts/check-public-files.py':continue
        for kind,pattern in PATTERNS.items():
            if re.search(pattern,text):issues.append((rel,kind))
        if re.search(r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)\b',text) and rel not in {'backend/tests/test_automation.py','backend/tests/test_release.py'}:
            issues.append((rel,'private network address needs review'))
    return issues
if __name__=='__main__':
    files=list(public_files());issues=inspect(files)
    for path,kind in issues:print(kind+': '+path)
    print(f'Public file checks: {len(files)} selected files; {len(issues)} blocking candidates')
    raise SystemExit(bool(issues))
