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

    def test_board_people_history_final(self):
        import json
        extras.CONFIG_OVERRIDES.clear()
        b = extras.board_frame()
        for t in ('<span>이사장</span><strong>원용진</strong>', '<span>대표</span><strong>김동환</strong>',
                  '박춘노 · 김민수 · 김영철 · 이승민 · 이모세', '<span>사무국</span><strong>최지은 간사</strong>'):
            self.assertIn(t, b)
        self.assertNotIn('<span>감사</span>', b)
        people = (ROOT / 'content' / 'people.md').read_text(encoding='utf-8')
        for t in ('김민수 · 1기 대표 (2017~2025)', '정혜진 · 오지훈 간사 (2017~2020, 창립 때부터)',
                  '오수연 간사 (2021~2022)', '김동환 간사 (2020년 10월 선임, 2021~2022 활동)', '최현정 간사 (2022년 3월 선임)', '2025년 2월~2026년 3월',
                  '최지은 간사 (2026년 9월~)', '2026년 9월 2일 이사회'):
            self.assertIn(t, people)
        # 시트에 옛 문장이 남아 있어도 교정.json 으로 같은 결과가 나온다
        self.assertIn('김민수 · 1기 대표 (2017~2025)', build._corrected('people', '- 김민수 · 1기 대표 (2017~2024)'))
        hist = build._corrected('history', '2025년 1월: 김동환 대표 부임. 2월 이수경 연구원 합류.')
        self.assertIn('2025년 1월 31일: 김동환 대표 부임. 2월 이수경 연구원 합류(2026년 3월까지).', hist)
        h = (ROOT / 'content' / 'history.md').read_text(encoding='utf-8')
        self.assertIn('2026년 3월: 이수경 연구원 활동 마무리.', h)


if __name__ == '__main__':
    unittest.main()
