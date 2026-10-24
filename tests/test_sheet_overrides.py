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
