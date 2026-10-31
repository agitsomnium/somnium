"""Public build boundary and durable poster regression."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from extras import news_strip
from build import build

class PublicIsolationTest(unittest.TestCase):
    def test_two_expired_posters_use_existing_local_assets_with_base(self):
        posts=json.loads((ROOT/'data/catalog/instagram.json').read_text())
        html=news_strip(posts,base='/site')
        for name in ['somnium-love-portrait.png','somnium-gakkaseuro-portrait.png']:
            self.assertIn('/site/assets/posters/'+name,html)
            self.assertTrue((ROOT/'assets/posters'/name).is_file())

    def test_public_build_omits_local_classroom_and_all_private_sources(self):
        (ROOT/'dist').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'dist') as folder:
            dest=Path(folder)/'public'
            build(ROOT/'data/sample',dest)
            home=(dest/'index.html').read_text()
            self.assertNotIn('href="/classroom/"',home)
            self.assertFalse((dest/'classroom').exists())
            for f in dest.rglob('*'):
                if f.suffix in ['.html','.json','.xml','.txt','.js']:
                    text=f.read_text()
                    for forbidden in ['PRIVATE_EXTERNAL_NOTES','example.test','classroom_private','video_privacy','somnium_resource']:
                        self.assertNotIn(forbidden,text,str(f))
