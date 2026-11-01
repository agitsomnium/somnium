import json
import tempfile
import unittest
from pathlib import Path

from build_static import build

CONFIG = {'url': 'https://jdfrottxrdhglxtqvtyx.supabase.co', 'publishableKey': 'sb_publishable_test', 'service_role': 'MUST-NOT-COPY', 'smtp': 'MUST-NOT-COPY'}


class StaticPackage(unittest.TestCase):
    def build(self, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cfg = Path(tmp.name) / 'c.json'
        cfg.write_text(json.dumps(CONFIG))
        out = Path(tmp.name) / 'out'
        return out, build(cfg, out, **kw)

    def test_only_allowlisted_files_and_no_source_or_secrets(self):
        out, files = self.build()
        names = set(files)
        self.assertTrue({'index.html', 'app.js', 'guide/index.html', 'runtime-config.json', '_headers'} <= names)
        self.assertFalse([n for n in names if n.endswith(('.py', '.json')) and n != 'runtime-config.json'])
        self.assertFalse([n for n in names if 'guide-data' in n or 'node_modules' in n or n.startswith('..')])
        blob = b''.join((out / n).read_bytes() for n in names if not n.endswith('.woff2'))
        self.assertNotIn(b'MUST-NOT-COPY', blob)

    def test_runtime_config_keys_and_reviewers(self):
        out, _ = self.build(reviewers=['reviewer@example.test'])
        cfg = json.loads((out / 'runtime-config.json').read_text())
        self.assertEqual(set(cfg), {'url', 'publishableKey', 'testEmails', 'profileMode'})
        self.assertEqual(cfg['testEmails'], ['agit.somnium@gmail.com', 'reviewer@example.test'])

    def test_headers_and_public_guide_choice(self):
        out, _ = self.build(guide='public')
        headers = (out / '_headers').read_text()
        for needle in ('Cache-Control: no-store', 'X-Robots-Tag: noindex', "frame-ancestors 'none'", "default-src 'none'"):
            self.assertIn(needle, headers)
        self.assertNotIn('강사 공개 허락 확인 전', (out / 'guide/index.html').read_text(encoding='utf-8'))

    def test_rejects_wrong_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'c.json'
            cfg.write_text(json.dumps({'url': 'https://other.supabase.co', 'publishableKey': 'sb_publishable_x'}))
            with self.assertRaises(ValueError):
                build(cfg, Path(tmp) / 'o')


if __name__ == '__main__':
    unittest.main()
