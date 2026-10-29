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
        self.assertNotIn('facebook.com/plugins', html)
        self.assertNotIn('javascript:', html)


class NoShortsTest(unittest.TestCase):
    def test_new_and_cached_reels_excluded_before_limit(self):
        import sys
        import tempfile
        sys.path.insert(0, str(ROOT / 'scripts'))
        from fetch_social import normalize
        from extras import load_instagram, news_strip
        image = 'https://cdn.example/post.jpg'
        reel = {'link': 'https://www.instagram.com/reel/SHORT/', 'image': image, 'caption': '쇼츠'}
        poster = {'link': 'https://www.instagram.com/p/POST/', 'image': image, 'caption': '모임 안내'}
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'instagram.json').write_text(json.dumps([reel, poster]))
            self.assertEqual(load_instagram(folder, limit=1), [poster])
        html = news_strip([reel, poster])
        self.assertNotIn(reel['link'], html)
        self.assertIn(poster['link'], html)
        self.assertEqual(news_strip([reel]), '')
        raw = [{'permalink': reel['link'], 'thumbnailUrl': image},
               {'permalink': poster['link'], 'mediaType': 'VIDEO', 'thumbnailUrl': image},
               {'permalink': poster['link'], 'mediaProductType': 'REELS', 'thumbnailUrl': image},
               {'permalink': poster['link'], 'mediaType': 'CAROUSEL_ALBUM', 'mediaUrl': image}]
        self.assertEqual(len(normalize(raw)), 1)


class PosterTest(unittest.TestCase):
    def test_sonjeol_uses_preserved_poster(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from extras import news_strip
        post = {'link': 'https://www.instagram.com/p/POST/', 'image': 'https://cdn.example/expired.jpg',
                'caption': '[10월 솜니움 북클럽 | 손절사회]'}
        html = news_strip([post], base='/preview')
        self.assertIn('src="/preview/assets/sonjeol.webp"', html)
        self.assertNotIn('expired.jpg', html)
        self.assertTrue((ROOT / 'assets/sonjeol.webp').is_file())
