import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from extras import news_strip, post_image
import fetch_social
from build import validate_local_images


class NewsImageIntegrityTest(unittest.TestCase):
    def test_all_visible_news_posters_load_eagerly_with_asset_version(self):
        posts = [
            {'link': 'https://www.instagram.com/p/DeylqA_hGrj/', 'image': 'https://expired.example/a.jpg', 'text': '[북클럽 | 이 망할 세상에서 사랑이라니!]'},
            {'link': 'https://www.instagram.com/p/Dev3vMGBHKg/', 'image': 'https://expired.example/b.jpg', 'text': '[북클럽 | 가까스로-있음]'},
        ]
        html = news_strip(posts)
        self.assertEqual(html.count('loading="eager"'), 2)
        self.assertNotIn('loading="lazy"', html)
        self.assertNotIn('expired.example', html)
        for name in ('bookclub-love-poster.jpg', 'bookclub-close-poster.jpg'):
            self.assertRegex(html, name.replace('.', r'\.') + r'\?v=[a-f0-9]{12}')

    def test_new_bytes_create_new_url_without_reusing_an_old_cached_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(fetch_social, 'ROOT', Path(folder)):
            path = Path(folder) / 'data/catalog/instagram-images/NEW.jpg'
            path.parent.mkdir(parents=True)
            post = {'link': 'https://www.instagram.com/p/NEW/'}
            path.write_bytes(b'old bytes')
            first = post_image(post)
            path.write_bytes(b'repaired bytes')
            self.assertNotEqual(post_image(post), first)

    def test_missing_and_truncated_image_block_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            (stage / 'assets').mkdir()
            (stage / 'index.html').write_text('<img src="/preview/assets/poster.jpg?v=123">')
            with self.assertRaisesRegex(ValueError, 'Missing local image'):
                validate_local_images(stage, '/preview')
            (stage / 'assets/poster.jpg').write_bytes(b'\xff\xd8\xfftruncated')
            with self.assertRaisesRegex(ValueError, 'Invalid local image'):
                validate_local_images(stage, '/preview')
            shutil.copyfile(ROOT / 'assets/bookclub-love-poster.jpg', stage / 'assets/poster.jpg')
            self.assertEqual(validate_local_images(stage, '/preview'), 1)
