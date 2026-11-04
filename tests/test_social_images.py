import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_social
from extras import post_image, news_strip, social_feeds

POST = {'link':'https://www.instagram.com/p/De3FtRxATMA/', 'image':'https://behold.pictures/expired.jpg', 'text':'연구소 소개'}

class SocialImagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = mock.patch.object(fetch_social, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @mock.patch.object(fetch_social.urllib.request, 'urlopen')
    def test_saved_original_survives_remote_expiry_on_both_surfaces(self, download):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'\xff\xd8\xffsaved-image'
        download.return_value = response
        fetch_social.cache_images([POST])
        self.assertEqual(fetch_social.cached_image(POST).read_bytes(), b'\xff\xd8\xffsaved-image')
        for render in (news_strip, social_feeds):
            self.assertIn('/assets/instagram/De3FtRxATMA.jpg', render([POST]))
            self.assertNotIn('behold.pictures', render([POST]))
        download.side_effect = TimeoutError()
        fetch_social.cache_images([POST])
        self.assertEqual(download.call_count, 1)
        self.assertEqual(post_image(POST, '/somnium'), '/somnium/assets/instagram/De3FtRxATMA.jpg')

    @mock.patch.object(fetch_social.urllib.request, 'urlopen')
    def test_missing_or_invalid_image_keeps_card_with_brand_cover(self, download):
        for failure in (TimeoutError(), None):
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = b'<html>expired</html>'
            download.side_effect = failure
            download.return_value = response
            fetch_social.cache_images([POST])
            self.assertIsNone(fetch_social.cached_image(POST))
            self.assertIn('/assets/somnium_wordmark_on_navy.svg', news_strip([POST]))
            self.assertIn(POST['link'], news_strip([POST]))
            self.assertNotIn('behold.pictures', news_strip([POST]))

    @mock.patch.object(fetch_social.urllib.request, 'urlopen')
    def test_no_download_for_reels_or_unsafe_paths_or_hosts(self, download):
        fetch_social.cache_images([
            {**POST,'link':'https://www.instagram.com/reel/abc/'},
            {**POST,'link':'https://www.instagram.com/p/../'},
            {**POST,'image':'http://behold.pictures/test.jpg'},
            {**POST,'image':'https://example.com/test.jpg'},
        ])
        download.assert_not_called()

    @mock.patch.object(fetch_social.urllib.request, 'urlopen')
    def test_feed_failure_still_preserves_and_uses_saved_image(self, download):
        folder = self.root / 'data/catalog'
        (folder / 'instagram-images').mkdir(parents=True)
        (folder / 'instagram-images/De3FtRxATMA.jpg').write_bytes(b'\xff\xd8\xffsaved')
        (folder / 'instagram.json').write_text(json.dumps([POST]))
        target = self.root / 'live.json'
        fetch_social._fallback(target)
        self.assertEqual(json.loads(target.read_text()), [POST])
        self.assertIn('/assets/instagram/De3FtRxATMA.jpg', post_image(POST))
        download.assert_not_called()
