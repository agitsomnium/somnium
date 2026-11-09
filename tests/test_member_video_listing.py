import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import videos_page
from extras import load_videos

class MemberVideoListing(unittest.TestCase):
    def test_stale_feed_cannot_reintroduce_member_video(self):
        public = {'id': 'public12345', 'title': '공개 강의'}
        member = {'id': 'member12345', 'title': '회원 강의', 'member_only': True}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cat = root / 'catalog.json'
            cat.write_text(json.dumps([member, public]))
            (root / 'youtube.json').write_text(json.dumps([member, public]))
            with patch.object(videos_page, 'CATALOG', cat):
                for rows in (videos_page.load_catalog([member, public]), load_videos(root)):
                    self.assertEqual([r['id'] for r in rows], ['public12345'])
            self.assertEqual(len(json.loads(cat.read_text())), 2)
