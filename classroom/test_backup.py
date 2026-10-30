"""A recoverable backup must retain rights, strip login secrets and reject corruption."""
import json
import tempfile
import unittest
from pathlib import Path
from backup_trial import snapshot, sha
from server import Trial

class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.source=self.root/'source'
        self.trial=Trial(self.source)
        (self.source/'video.mp4').write_bytes(b'synthetic video')
        (self.source/'notes.txt').write_text('private canary')
        with self.trial.connect() as db:
            db.execute("insert into lessons(id,title,audience,published,video,material) values ('one','lecture','supporter',1,'video.mp4','notes.txt')")
            db.execute("insert into sessions values ('secret','admin.one@example.test',9999999999,'csrf')")
            self.trial.issue(db,'admin.one@example.test','login')
            db.execute("insert into supporters(email,qualified,review_state) values ('member@example.test',1,'qualified')")
            db.execute("insert into orders(id,email,target_type,target_id,status,created_at) values ('order','member@example.test','lesson','one','confirmed',1)")
    def tearDown(self):
        self.temp.cleanup()
    def test_roundtrip_rights_integrity_and_authentication_removal(self):
        saved=self.root/'backup'
        result=snapshot(self.source,saved)
        self.assertTrue(result['authentication_removed'])
        restored=self.root/'restored'
        snapshot(saved,restored)
        trial=Trial(restored)
        with trial.connect() as db:
            self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('select count(*) from sessions').fetchone()[0],0)
            self.assertEqual(db.execute('select count(*) from otps').fetchone()[0],0)
            self.assertEqual(db.execute("select status from orders where id='order'").fetchone()[0],'confirmed')
            self.assertEqual(db.execute("select qualified from supporters where email='member@example.test'").fetchone()[0],1)
        self.assertEqual((restored/'notes.txt').read_text(),'private canary')
        with self.assertRaises(ValueError): snapshot(self.source,saved)
    def test_modified_missing_unlisted_and_symlink_material_are_rejected(self):
        for kind in ('changed','missing','unlisted','symlink'):
            with self.subTest(kind=kind):
                saved=self.root/kind
                snapshot(self.source,saved)
                file=saved/'notes.txt'
                if kind=='changed': file.write_text('changed')
                if kind=='missing': file.unlink()
                if kind=='symlink':
                    file.unlink(); file.symlink_to(self.source/'notes.txt')
                if kind=='unlisted':
                    manifest=json.loads((saved/'backup-manifest.json').read_text())
                    del manifest['notes.txt']
                    (saved/'backup-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError): snapshot(saved,self.root/('reject-'+kind))
