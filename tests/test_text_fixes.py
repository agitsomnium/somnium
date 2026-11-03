import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build  # noqa: E402
import extras  # noqa: E402
import pages  # noqa: E402


class TextFixes(unittest.TestCase):
    def test_bold_and_link(self):
        h = build.markdown('- **굵게** · [링크](https://a.b/c) · **[묶음](https://a.b)**')
        self.assertIn('<strong>굵게</strong>', h)
        self.assertIn('<a href="https://a.b/c">링크</a>', h)
        self.assertIn('<strong><a href="https://a.b">묶음</a></strong>', h)
        self.assertNotIn('**', h)
        self.assertNotIn('<strong>', build.markdown('곱셈 2 ** 3 ** 4'))

    def test_empty_board_seats_hidden(self):
        extras.CONFIG_OVERRIDES.clear()
        html = extras.board_frame()
        self.assertNotIn('명단 정리 중', html)
        self.assertIn('박춘노', html)

    def test_bookclub_numbers_by_date(self):
        rows = [{'id': 'b', '제목': '11월 북클럽 1', '도서': '가까스로-있음', '날짜': '2026-11-12;2026-11-19'},
                {'id': 'c', '제목': '11월 북클럽 2', '도서': '이 망할 세상에서 사랑이라니!', '날짜': '2026-11-10'},
                {'id': 'a', '제목': '10월 북클럽', '도서': '손절사회', '날짜': '2026-10-20'}]
        labels = [l for _, l in pages.bookclub_labels(rows)]
        self.assertEqual(labels, ['10월 북클럽 · 『손절사회』',
                                  '11월 북클럽 1 · 『이 망할 세상에서 사랑이라니!』',
                                  '11월 북클럽 2 · 『가까스로-있음』'])

    def test_corrections_apply_and_skip(self):
        t = '2019년 10월 18일:\n\n“조국 장관 논란” 이슈 토론회.'
        self.assertIn('2019년 10월 18일: “조국', build._corrected('history', t))
        self.assertEqual(build._corrected('history', '이미 고친 글'), '이미 고친 글')


if __name__ == '__main__':
    unittest.main()
