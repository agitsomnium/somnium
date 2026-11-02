import copy
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from build_guide import DATA, render
from serve import handler

WEB = Path(__file__).resolve().parent
DATA_JSON = json.loads(DATA.read_text(encoding='utf-8'))
MEDIA = re.compile(r'(youtu\.be/|youtube\.com/|vimeo\.com/|i\.ytimg\.com|\.pdf)', re.I)
# 2026-11-02: the operator decided that lecturer names within the already-published introductions are shown; no series is pending now.
# The pending mechanism (drop in public, badge in review) stays and is tested on a copy where one series is marked pending.
SAMPLE = copy.deepcopy(DATA_JSON)
SAMPLE['series'][1]['permission'] = 'pending'
PENDING_NAMES = [n.split(' 외')[0] for s in SAMPLE['series'] if s['permission'] != 'public' for n in s['lecturers'].split(' · ') if n]
ALL_NAMES = [n.split(' 외')[0] for s in DATA_JSON['series'] for n in s['lecturers'].split(' · ') if n]
ORDER_MARK = '처음이라면 이 순서로'


def text_of(html):
    return re.sub(r'<[^>]+>', ' ', html)


class GuideRender(unittest.TestCase):
    def test_public_shows_all_introduced_lecturers_now(self):
        html = render(DATA_JSON, 'public')
        self.assertGreater(len(ALL_NAMES), 10)
        for name in ALL_NAMES:
            self.assertIn(name, html)
        self.assertNotIn('badge', html)

    def test_public_drops_pending_lecturers_and_keeps_public_one(self):
        html = render(SAMPLE, 'public')
        self.assertTrue(PENDING_NAMES)
        for name in PENDING_NAMES:
            self.assertNotIn(name, html)
        self.assertIn('정용택', html)

    def test_review_marks_every_pending_series(self):
        html = render(SAMPLE, 'review')
        pending = [s for s in SAMPLE['series'] if s['permission'] != 'public' and s['lecturers']]
        self.assertEqual(html.count('강사 공개 허락 확인 전'), len(pending))
        for name in PENDING_NAMES:
            self.assertIn(name, html)

    def test_unapproved_order_is_omitted_from_public_but_marked_in_review(self):
        self.assertFalse(DATA_JSON['order']['approved'])
        public = render(DATA_JSON, 'public')
        self.assertNotIn(ORDER_MARK, public)
        self.assertNotIn('추천 순서', public)
        review = render(DATA_JSON, 'review')
        self.assertIn(ORDER_MARK, review)
        self.assertIn('운영진 확인 전 초안', review)

    def test_approved_order_appears_in_public_without_draft_label(self):
        data = copy.deepcopy(DATA_JSON)
        data['order']['approved'] = True
        public = render(data, 'public')
        self.assertIn(ORDER_MARK, public)
        self.assertNotIn('운영진 확인 전 초안', public)
        self.assertIn('추천 순서', public)

    def test_lecture_count_is_stated_only_when_verified(self):
        unverified = copy.deepcopy(DATA_JSON)
        unverified['memberLectures']['verified'] = False
        self.assertNotRegex(text_of(render(unverified, 'public')), r'\d+\s*편')
        self.assertIn('원격 실조회 전', text_of(render(unverified, 'review')))
        data = copy.deepcopy(DATA_JSON)
        data['memberLectures']['verified'] = True
        self.assertIn(f'회원 강의 {data["memberLectures"]["count"]}편', text_of(render(data, 'public')))

    def test_no_private_media_or_invented_numbers(self):
        for mode in ('review', 'public'):
            html = render(DATA_JSON, mode)
            self.assertIsNone(MEDIA.search(html))
            self.assertNotRegex(text_of(html), r'회원\s*\d+\s*명|목표\s*\d')

    def test_flow_links_and_escaping(self):
        html = render(DATA_JSON, 'public')
        self.assertEqual([s['n'] for s in DATA_JSON['flow']], [1, 2, 3, 4])
        self.assertEqual(set(re.findall(r'href="(https?://[^"]+)"', html)),
                         {'https://somniumagit.com', 'https://somniumagit.com/participate/', 'https://online.mrm.or.kr/PCjx2kb'})
        data = copy.deepcopy(DATA_JSON)
        data['hero']['lead'] = '<script>alert(1)</script>'
        self.assertNotIn('<script>alert', render(data, 'public'))


class GuideServedFromCleanBuild(unittest.TestCase):
    """Build into an empty directory, then read /guide/ over real HTTP."""

    def serve(self, dist, mode):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler({}, 0))
        port = httpd.server_port
        httpd.RequestHandlerClass = handler({'url': 'https://example.invalid', 'publishableKey': 'sb_publishable_test'}, port, mode, Path(dist))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        return port

    def get(self, port, path):
        conn = HTTPConnection('127.0.0.1', port)
        conn.request('GET', path, headers={'Host': f'127.0.0.1:{port}'})
        res = conn.getresponse()
        body = res.read()
        conn.close()
        return res.status, body.decode('utf-8', 'replace')

    def build(self, dist, mode):
        subprocess.run([sys.executable, str(WEB / 'build_guide.py'), '--mode', mode, '--out-dir', str(dist)], check=True, capture_output=True)

    def test_public_only_build_serves_public_content(self):
        with tempfile.TemporaryDirectory() as dist:
            self.build(dist, 'public')
            status, body = self.get(self.serve(dist, 'public'), '/guide/')
            self.assertEqual(status, 200)
            for name in ALL_NAMES:
                self.assertIn(name, body)
            self.assertNotIn('운영진 검토본', body)
            self.assertNotIn(ORDER_MARK, body)
            self.assertNotIn('badge', body)
            self.assertEqual(self.get(self.serve(dist, 'review'), '/guide/')[0], 404)

    def test_public_server_never_falls_back_to_leftover_review_file(self):
        with tempfile.TemporaryDirectory() as dist:
            self.build(dist, 'all')
            self.assertNotIn('운영진 검토본', self.get(self.serve(dist, 'public'), '/guide/')[1])
            self.assertIn('운영진 검토본', self.get(self.serve(dist, 'review'), '/guide/')[1])

    def test_empty_build_is_404_not_stale(self):
        with tempfile.TemporaryDirectory() as dist:
            self.assertEqual(self.get(self.serve(dist, 'public'), '/guide/')[0], 404)


if __name__ == '__main__':
    unittest.main()
