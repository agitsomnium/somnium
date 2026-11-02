import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import data  # noqa: E402


class SheetOverrides(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for f in (ROOT / 'data' / 'sample').glob('*.csv'):
            shutil.copy(f, self.d)

    def tearDown(self):
        shutil.rmtree(self.d)

    def write(self, name, rows):
        with open(self.d / (name + '.csv'), 'w', encoding='utf-8', newline='') as f:
            csv.writer(f).writerows(rows)

    def test_optional_tabs_override(self):
        self.write('페이지글', [['id', '제목', '본문', '공개'], ['about', '소개', '# 새 소개\n본문', '예'], ['nope', 'x', 'y', '예']])
        self.write('계좌', [['용도', '설명', '은행', '번호', '예금주', '안내', '정렬', '공개'], ['후원', '', '국민은행', '1-2-3', '솜니움', '', '1', '예']])
        self.write('연락', [['항목', '값'], ['이메일', 'a@b.c'], ['인스타 주소', 'javascript:x'], ['페이스북 주소', 'https://facebook.com/x']])
        t = data.load_tables(self.d)
        pages, cfg = data.overrides(t)
        self.assertEqual(list(pages), ['about'])
        self.assertEqual(cfg['accounts'][0]['번호'], '1-2-3')
        self.assertEqual(cfg['email'], 'a@b.c')
        self.assertNotIn('instagram', cfg)  # https 아닌 주소는 무시
        self.assertEqual(cfg['facebook']['url'], 'https://facebook.com/x')

    def test_without_optional_tabs(self):
        pages, cfg = data.overrides(data.load_tables(self.d))
        self.assertEqual((pages, cfg), ({}, {}))


if __name__ == '__main__':
    unittest.main()


class SheetFormats(unittest.TestCase):
    def test_dates_times_from_google(self):
        self.assertEqual(data.norm_date('2026. 9. 17'), '2026-09-17')
        self.assertEqual(data.norm_date('2026/11/5;2026. 11. 12'), '2026-11-05;2026-11-12')
        self.assertEqual(data.norm_date('2026-10-01'), '2026-10-01')
        self.assertEqual(data.norm_time('오후 7:00:00'), '19:00')
        self.assertEqual(data.norm_time('19:00:00'), '19:00')
        self.assertEqual(data.norm_time('7:30 PM'), '19:30')
        self.assertEqual(data.norm_time('19:00'), '19:00')
        self.assertEqual(data.norm_date('46282'), '2026-09-17')
        self.assertEqual(data.norm_date('2026. 11. 10 오전 12:00:00'), '2026-11-10')
        self.assertEqual(data.norm_time('0.7916666667'), '19:00')


class SettleStatusAndPlaceTest(unittest.TestCase):
    """날짜가 지난 모집중·진행중은 자동으로 종료, 장소 표기는 한 가지로."""

    def test_ended_dates_override_manual_status(self):
        import datetime
        import sheet_friendly as sf
        today = datetime.date(2026, 11, 2)
        self.assertEqual(sf.settle_status({"상태": "진행중", "시작일": "2026-09-17", "종료일": "2026-10-29"}, today, ("시작일", "종료일")), "종료")
        self.assertEqual(sf.settle_status({"상태": "진행중", "날짜": "2026-10-20;2026-10-27"}, today, ("날짜",)), "종료")
        self.assertEqual(sf.settle_status({"상태": "모집중", "날짜": "2026-11-12;2026-11-19"}, today, ("날짜",)), "모집중")
        self.assertEqual(sf.settle_status({"상태": "예고"}, today, ("시작일", "종료일")), "예고")
        self.assertEqual(sf.settle_status({"상태": "취소", "날짜": "2026-10-01"}, today, ("날짜",)), "취소")
        self.assertEqual(sf.settle_status({"상태": "", "날짜": "2026-10-01"}, today, ("날짜",)), "종료")

    def test_place_unified(self):
        import sheet_friendly as sf
        for v in ("솜니움 모임공간(합정) · 줌", "솜니움 사무실 · Zoom 병행", "솜니움 사무실(합정–상수역 사이) · Zoom 병행",
                  "솜니움 사무실(합정역–상수역 사이) · 온라인 Zoom 병행"):
            self.assertEqual(sf.normalize_place(v), sf.PLACE_OFFICE)
        self.assertEqual(sf.normalize_place("서울 마포구 독막로 43, 2층"), "서울 마포구 독막로 43, 2층")

    def test_clip_at_word_or_sentence(self):
        from fetch_social import clip
        t = "첫 문장입니다. 두 번째 문장은 조금 더 깁니다. 세 번째 문장이 이어집니다 그리고 계속됩니다"
        c = clip(t, 40)
        self.assertTrue(c.endswith("…"))
        self.assertEqual(c, "첫 문장입니다. 두 번째 문장은 조금 더 깁니다…")
        self.assertEqual(clip("짧은 글", 40), "짧은 글")
        w = clip("가나다라 마바사아 자차카타 파하거너 더러머버 서어저처", 20)
        self.assertTrue(w.endswith("…") and not w[:-1].endswith(" "))
        self.assertIn(w[:-1], "가나다라 마바사아 자차카타 파하거너 더러머버 서어저처")
        self.assertTrue(w[:-1].split()[-1] in "가나다라 마바사아 자차카타 파하거너 더러머버 서어저처".split())
