import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extras import news_strip, social_feeds
class DurablePosters(unittest.TestCase):
 def test_expired_remote_urls_use_owned_local_files_on_both_surfaces(self):
  posts=[{'link':'https://www.instagram.com/p/DeylqA_hGrj/','image':'https://behold.pictures/expired-love.jpg','text':'[11월 솜니움 북클럽2 | 이 망할 세상에서 사랑이라니!]'}, {'link':'https://www.instagram.com/p/Dev3vMGBHKg/','image':'https://behold.pictures/expired-close.jpg','text':'[11월 솜니움 북클럽1 | 가까스로-있음]'}]
  for render in (news_strip,social_feeds):
   html=render(posts)
   self.assertNotIn('behold.pictures',html)
   for name in ('bookclub-love-poster.jpg','bookclub-close-poster.jpg'):
    self.assertIn('/assets/'+name,html)
    self.assertTrue((Path(__file__).resolve().parents[1]/'assets'/name).is_file())
