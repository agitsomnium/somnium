import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import insta_events  # noqa: E402

GAKKA = """[11월 솜니움 북클럽1 | 가까스로-있음]

김홍중의 《가까스로-있음》(이음)을 함께 읽습니다.

*일시 | 2026년 11월 12·19·26일(목) 저녁 7–9시 · 총 3회
*장소 | 솜니움 사무실(합정역–상수역 사이) · 온라인 Zoom 병행
*참가비 | 일반 3만원 · 솜니움 후원회원 무료 · 아지트솜니움 회원 1만5천원
*신청 | QR코드 또는 프로필 링크"""
LECTURE = """[12월 솜니움 특강 | 시험 특강]
연구자와 함께합니다.
*일시 | 12월 3일(수) 오후 2-4시
*장소 | 솜니움 사무실
*신청 | https://forms.gle/abc123"""


def empty():
    return {'세미나': [], '회차': [], '북클럽': []}


class InstaEvents(unittest.TestCase):
    def test_bookclub(self):
        ev = insta_events.parse_post({'text': GAKKA, 'link': 'https://www.instagram.com/somnium_agit/p/Dev3vMGBHKg/'})
        self.assertEqual(ev['days'], ['2026-11-12', '2026-11-19', '2026-11-26'])
        self.assertEqual(ev['time'], '19:00')
        self.assertEqual(ev['kind'], '북클럽')

    def test_merge_and_dedupe(self):
        t = empty()
        posts = [{'text': GAKKA, 'link': 'https://www.instagram.com/somnium_agit/p/Dev3vMGBHKg/', 'date': '2026-10-21'},
                 {'text': LECTURE, 'link': 'https://www.instagram.com/somnium_agit/p/XYZ/', 'date': '2026-10-30'}]
        self.assertEqual(insta_events.merge(t, posts, datetime.date(2026, 10, 24)), 2)
        self.assertEqual(t['북클럽'][0]['날짜'], '2026-11-12;2026-11-19;2026-11-26')
        self.assertEqual(t['세미나'][0]['신청_url'], 'https://forms.gle/abc123')
        self.assertEqual(t['회차'][0]['시간'], '14:00')
        self.assertEqual(insta_events.merge(t, posts, datetime.date(2026, 10, 24)), 0)  # 이미 있으면 안 붙인다

    def test_short_year_and_commas(self):
        ev = insta_events.parse_post({'text': '[10월 솜니움 북클럽 | 손절사회]\n소개\n*일시 |  26년 10월 20일, 27일 (화) 저녁 7-9시 (2회)\n*신청 |  https://forms.gle/zn5P72E1hfjF2iae8'})
        self.assertEqual(ev['days'], ['2026-10-20', '2026-10-27'])
        self.assertEqual(ev['link'], 'https://forms.gle/zn5P72E1hfjF2iae8')

    def test_ignores_plain_post(self):
        self.assertIsNone(insta_events.parse_post({'text': '오늘 세미나 사진입니다'}))


if __name__ == '__main__':
    unittest.main()
