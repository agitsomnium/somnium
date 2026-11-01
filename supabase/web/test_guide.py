import json
import re
import unittest
from build_guide import DATA, render

DATA_JSON = json.loads(DATA.read_text(encoding='utf-8'))
VIDEO_ID = re.compile(r'(youtu\.be/|youtube\.com/|vimeo\.com/|i\.ytimg\.com|\.pdf)', re.I)


class GuideBuild(unittest.TestCase):
    def test_public_drops_pending_lecturers_and_badges(self):
        html = render(DATA_JSON, 'public')
        for s in DATA_JSON['series']:
            if s['permission'] == 'pending':
                for name in s['lecturers'].split(' · '):
                    self.assertNotIn(name.split(' 외')[0], html)
        self.assertNotIn('badge', html)
        self.assertIn('정용택', html)

    def test_review_marks_every_pending_series(self):
        html = render(DATA_JSON, 'review')
        pending = [s for s in DATA_JSON['series'] if s['permission'] != 'public' and s['lecturers']]
        self.assertEqual(html.count('강사 공개 허락 확인 전'), len(pending))
        self.assertIn('운영진 확인 전 초안', html)

    def test_no_private_media_references(self):
        for mode in ('review', 'public'):
            self.assertIsNone(VIDEO_ID.search(render(DATA_JSON, mode)))

    def test_flow_has_four_steps_and_only_known_links(self):
        html = render(DATA_JSON, 'public')
        self.assertEqual([s['n'] for s in DATA_JSON['flow']], [1, 2, 3, 4])
        hrefs = set(re.findall(r'href="(https?://[^"]+)"', html))
        self.assertEqual(hrefs, {'https://somniumagit.com', 'https://somniumagit.com/participate/', 'https://online.mrm.or.kr/PCjx2kb'})

    def test_no_invented_numbers(self):
        text = re.sub(r'<[^>]+>', ' ', render(DATA_JSON, 'public'))
        self.assertIn('회원 강의 93편', text)
        self.assertNotRegex(text, r'회원\s*\d+\s*명|목표\s*\d')

    def test_escapes_markup(self):
        data = json.loads(json.dumps(DATA_JSON))
        data['hero']['lead'] = '<script>alert(1)</script>'
        self.assertNotIn('<script>alert', render(data, 'public'))


if __name__ == '__main__':
    unittest.main()
