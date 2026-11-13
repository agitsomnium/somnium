import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import extras  # noqa: E402
import home_plaza  # noqa: E402
import pages  # noqa: E402

SRC = lambda n: (ROOT / 'scripts' / n).read_text(encoding='utf-8')


class Review20261113(unittest.TestCase):
    def test_member_lecture_count_single_source(self):
        for name in ('home_plaza.py', 'pages.py'):
            self.assertIsNone(re.search(r'지난 강의 \d+편', SRC(name)), name)
        self.assertIn('지난 강의 %d편' % extras.MEMBER_LECTURE_COUNT, home_plaza.MEMBER_STRIP)

    def test_accounting_wording(self):
        self.assertNotIn('로그인한 회원이 볼 수 있습니다', SRC('pages.py'))
        self.assertIn('회계 보고(이사 전용)', SRC('render.py'))

    def test_no_oopy_links_or_source_footer(self):
        p = SRC('pages.py')
        self.assertNotIn('href="https://somnium.oopy.io', p)
        self.assertNotIn('자료출처', p)

    def test_bookclub_names_match_labels(self):
        rows = [{'id': 'b', '제목': '11월 북클럽 1', '도서': '가까스로-있음', '날짜': '2026-11-12;2026-11-19'},
                {'id': 'c', '제목': '11월 북클럽 2', '도서': '이 망할 세상에서 사랑이라니!', '날짜': '2026-11-10'}]
        self.assertEqual(extras._bookclub_names(rows), ['11월 북클럽 2', '11월 북클럽 1'])
        labels = {r['id']: l for r, l in pages.bookclub_labels(rows)}
        self.assertTrue(labels['b'].startswith('11월 북클럽 2'))
        self.assertTrue(labels['c'].startswith('11월 북클럽 1'))


if __name__ == '__main__':
    unittest.main()
