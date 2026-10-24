import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'upstream.py'
spec = importlib.util.spec_from_file_location('upstream', SCRIPT)
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


class UpdateTests(unittest.TestCase):
    def test_verification_is_due_after_28_days_or_missing_record(self):
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(upstream.verification_due(root, now))
            record = root / 'maintenance.json'
            record.write_text(json.dumps({'last_verified': (now - timedelta(days=27)).isoformat()}))
            self.assertFalse(upstream.verification_due(root, now))
            record.write_text(json.dumps({'last_verified': (now - timedelta(days=28)).isoformat()}))
            self.assertTrue(upstream.verification_due(root, now))

    def fixture(self, root):
        app = root / 'syncclipboard_server'
        app.mkdir()
        digest = 'sha256:' + '1' * 64
        (app / 'Dockerfile').write_text('FROM jericx/syncclipboard-server@' + digest + '\nRUN true\n')
        config = {'version': '0.1.1', 'options': {'username': 'syncclipboard', 'password': ''}}
        (app / 'config.json').write_text(json.dumps(config))
        (root / 'upstream.json').write_text(json.dumps({'digest': digest, 'version': '3.3.3'}))
        (app / 'CHANGELOG.md').write_text('# Changelog\n\nInitial release.\n')
        return app

    def test_changed_digest_increments_version_and_preserves_options(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.fixture(root)
            self.assertTrue(upstream.prepare(root, 'sha256:' + '2' * 64))
            config = json.loads((app / 'config.json').read_text())
            self.assertEqual(config['version'], '0.1.2')
            self.assertEqual(config['options'], {'username': 'syncclipboard', 'password': ''})
            self.assertIn('2' * 64, (app / 'Dockerfile').read_text())

    def test_unchanged_digest_does_not_change_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.fixture(root)
            before = (app / 'config.json').read_bytes()
            self.assertFalse(upstream.prepare(root, 'sha256:' + '1' * 64))
            self.assertEqual(before, (app / 'config.json').read_bytes())

    def test_invalid_digest_changes_nothing(self):
        for digest in ['latest', 'sha256:123', 'sha256:' + 'g' * 64, 'sha256:' + 'a' * 64 + '\nRUN bad']:
            with self.subTest(digest=digest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                app = self.fixture(root)
                before = (app / 'Dockerfile').read_bytes()
                with self.assertRaises(ValueError):
                    upstream.prepare(root, digest)
                self.assertEqual(before, (app / 'Dockerfile').read_bytes())

    def test_unsupported_version_changes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.fixture(root)
            config = json.loads((app / 'config.json').read_text())
            config['version'] = 'invalid'
            (app / 'config.json').write_text(json.dumps(config))
            before = (app / 'Dockerfile').read_bytes()
            with self.assertRaises(ValueError):
                upstream.prepare(root, 'sha256:' + '2' * 64)
            self.assertEqual(before, (app / 'Dockerfile').read_bytes())


if __name__ == '__main__':
    unittest.main()
