"""Offline source/packaging checks; these do NOT execute Docker/Compose."""
import json
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ReleaseStatic(unittest.TestCase):
    def test_versions_agree(self):
        version=json.loads((ROOT/'frontend/package.json').read_text())['version']
        self.assertEqual(version,'0.5.0-rc.1')
        for file in ['backend/app/config.py','backend/app/schemas.py','scripts/start-local.ps1','scripts/test-browser.ps1']:
            self.assertIn(version,(ROOT/file).read_text())

    def test_compose_topology_and_migration_gate(self):
        compose=(ROOT/'compose.yaml').read_text()
        for service in ['db','migrate','api','worker','frontend']:
            self.assertRegex(compose,rf'(?m)^  {service}:$')
        self.assertIn('service_completed_successfully',compose)
        self.assertIn('"-m", "app.worker"',compose)
        self.assertIn('"--health"',compose)
        self.assertIn('POSTGRES_PASSWORD:?',compose)
        self.assertNotIn('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS: "true"',compose)
        self.assertNotIn('app.store',(ROOT/'backend/Dockerfile').read_text())
        self.assertIn('tzdata==2026.5',(ROOT/'backend/requirements.txt').read_text())

    def test_container_contexts_and_private_files_excluded(self):
        for folder in ['backend','frontend']:
            self.assertIn('.env*',(ROOT/folder/'.dockerignore').read_text())
        ignore=(ROOT/'.gitignore').read_text()
        for entry in ['.env','.env.*','.local/','*.dump','work/']:
            self.assertIn(entry,ignore)

    def test_public_source_has_no_provider_credentials(self):
        excluded={'.local','.venv','node_modules','.pnpm-store','dist','work','previews','.git','.pytest_cache','__pycache__','.clearance'}
        extensions={'.py','.md','.json','.yaml','.yml','.ps1','.ts','.tsx','.js','.mjs','.env'}
        patterns=[re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{32,}'),re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'AKIA[0-9A-Z]{16}'),re.compile(r'\b[0-9]{6,20}:[A-Za-z0-9_-]{30,}\b'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
        findings=[]
        for path in ROOT.rglob('*'):
            if not path.is_file() or any(p in excluded for p in path.relative_to(ROOT).parts) or path.name=='test-release-static.py': continue
            if path.suffix not in extensions and path.name!='.env.example': continue
            source=path.read_text(encoding='utf-8',errors='replace')
            if any(pattern.search(source) for pattern in patterns): findings.append(str(path.relative_to(ROOT)))
        self.assertEqual(findings,[],f'Potential credentials in files: {findings}')

    def test_release_documents_and_security_headers(self):
        for file in ['README.md','docs/RELEASE_CHECKLIST.md','docs/DEPLOYMENT.md','docs/SECURITY.md','docs/architecture.md','docs/PORTFOLIO.md']:
            self.assertTrue((ROOT/file).is_file(),file)
        for file in ['frontend/nginx.conf','frontend/vite.config.mjs']:
            source=(ROOT/file).read_text()
            for header in ['Content-Security-Policy','X-Content-Type-Options','Referrer-Policy','frame-ancestors']:
                self.assertIn(header,source)

if __name__=='__main__': unittest.main(verbosity=2)
