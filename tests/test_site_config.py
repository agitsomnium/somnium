import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SiteConfigTest(unittest.TestCase):
    """운영진이 GitHub 웹에서 config/site.json 을 고쳐도 깨지지 않았는지 본다."""

    def test_site_json(self):
        cfg = json.loads((ROOT / 'config' / 'site.json').read_text(encoding='utf-8'))
        self.assertTrue(cfg.get('accounts'), '계좌가 비어 있습니다')
        for a in cfg['accounts']:
            for k in ('용도', '은행', '번호', '예금주'):
                self.assertTrue(a.get(k), '계좌 칸 비어 있음: %s' % k)
        for key in ('youtube', 'instagram', 'facebook'):
            url = (cfg.get(key) or {}).get('url', '')
            self.assertTrue(url.startswith('https://'), '%s 주소 확인' % key)
        for seat in cfg.get('board', []):
            self.assertIn('자리', seat)
            self.assertIn('이름', seat)


if __name__ == '__main__':
    unittest.main()


class SocialFeedTest(unittest.TestCase):
    """behold.so 피드 모양이 바뀌거나 이상한 값이 와도 안전한 것만 남는지 본다."""

    def test_normalize(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from fetch_social import normalize
        from extras import social_feeds
        raw = {'posts': [
            {'permalink': 'https://www.instagram.com/p/AAA/', 'mediaType': 'IMAGE', 'mediaUrl': 'https://cdn.example/a.jpg',
             'sizes': {'medium': {'mediaUrl': 'https://cdn.example/a-m.jpg'}}, 'caption': '모임 사진', 'timestamp': '2026-10-20T10:00:00Z'},
            {'permalink': 'javascript:alert(1)', 'mediaUrl': 'https://cdn.example/b.jpg'},
            {'permalink': 'https://www.instagram.com/p/CCC/', 'mediaType': 'VIDEO', 'mediaUrl': 'https://cdn.example/c.mp4'},
        ]}
        posts = normalize(raw)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['image'], 'https://cdn.example/a-m.jpg')
        html = social_feeds(posts)
        self.assertIn('ig-tile', html)
        self.assertIn('facebook.com/plugins/page.php', html)
        self.assertNotIn('javascript:', html)
