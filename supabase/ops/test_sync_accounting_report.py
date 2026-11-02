import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sync_accounting_report as report


class Store:
    def __init__(self):
        self.rows = []
        self.data = None
        self.saves = 0
        self.broken = False

    def find(self, name):
        return copy.deepcopy(self.rows)

    def object(self, name, data=None):
        if data is not None:
            self.data = data
        return b'wrong' if self.broken else self.data

    def save(self, m, f, name):
        self.saves += 1
        self.rows = [dict(id='report-id', title=m['title'].strip(), period=m['period'].strip(),
                          filename=f.name, enabled=m['publish'])]


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / 'summary.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\nsynthetic test only')
        self.manifest = dict(file='summary.pdf', title='Member report', period='2026-09',
                             sha256=hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                             member_safe=True, publish=False)
        self.path = self.root / 'manifest.json'

    def prepare(self):
        self.path.write_text(json.dumps(self.manifest))
        return report.prepare(self.path)

    def test_retry_has_no_duplicate_and_readback(self):
        args = self.prepare()
        store = Store()
        self.assertEqual(report.sync(*args, store), 'report-id')
        self.assertEqual(report.sync(*args, store), 'report-id')
        self.assertEqual(store.saves, 1)

    def test_bad_readback_never_registers(self):
        args = self.prepare()
        store = Store()
        store.broken = True
        with self.assertRaisesRegex(ValueError, 'readback'):
            report.sync(*args, store)
        self.assertEqual(store.saves, 0)

    def test_existing_hidden_report_not_republished(self):
        args = self.prepare()
        store = Store()
        report.sync(*args, store)
        args[0]['publish'] = True
        with self.assertRaisesRegex(ValueError, 'differs'):
            report.sync(*args, store)
        self.assertEqual(store.saves, 1)

    def test_changed_file_after_review_refused(self):
        self.pdf.write_bytes(b'%PDF-1.4\nchanged')
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.prepare()

    def test_unreviewed_refused(self):
        self.manifest['member_safe'] = False
        with self.assertRaisesRegex(ValueError, 'review'):
            self.prepare()

    def test_non_pdf_refused_even_named_pdf(self):
        self.pdf.write_text('raw ledger data')
        with self.assertRaisesRegex(ValueError, 'header'):
            self.prepare()

    def test_preview_never_constructs_backend(self):
        self.prepare()
        with patch('sys.argv', ['sync', '--manifest', str(self.path)]), patch.object(report, 'Backend') as backend:
            self.assertEqual(report.main(), 0)
            backend.assert_not_called()

    def test_sql_literals_quote_user_text(self):
        self.assertEqual(report.literal("a'b"), "'a''b'")


if __name__ == '__main__':
    unittest.main()
