import csv
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ['SITE_TODAY'] = '2026-10-24'
import data  # noqa: E402
import sheet_friendly  # noqa: E402
from make_easy_seed import FILES  # noqa: E402


def strip(t):
    return {k: [{x: y for x, y in r.items() if x != '_line'} for r in v] for k, v in t.items()}


class EasySheet(unittest.TestCase):
    def setUp(self):
        self.a = Path(tempfile.mkdtemp())
        self.b = Path(tempfile.mkdtemp())
        for stem, f in FILES.items():
            shutil.copy(ROOT / 'data/sheet_seed' / (f + '.csv'), self.a / (stem + '.csv'))
            shutil.copy(ROOT / 'data/sheet_seed/easy' / (f + '.csv'), self.b / (stem + '.csv'))

    def tearDown(self):
        shutil.rmtree(self.a)
        shutil.rmtree(self.b)

    def write(self, stem, rows):
        with open(self.b / (stem + '.csv'), 'w', encoding='utf-8', newline='') as fh:
            csv.writer(fh).writerows(rows)

    def test_easy_seed_same_as_internal(self):
        self.assertEqual(strip(data.load_tables(self.b)), strip(data.load_tables(self.a)))
        data.validate(data.load_tables(self.b))

    def test_plain_korean_input(self):
        """간사가 고유이름·상태 비우고, 강사 이름·세미나 제목·체크박스·쉬운 날짜로 적어도 된다."""
        self.write('세미나', [['제목', '상태', '시작일', '강사', '홈피에 보이기', '고유이름', '메모(아무거나)'],
                            ['새 세미나', '', '', '정용택 선생님', 'TRUE', '', '간사 메모'],
                            ['', '', '', '', 'FALSE', '', '']])
        self.write('회차', [['세미나', '회차', '날짜', '시간', '홈피에 보이기'],
                          ['새 세미나', '1회', '11/5', '저녁 7시 30분', 'TRUE'],
                          ['새 세미나', '2', '11월 12일', '오후 7:00:00', '']])
        t = data.validate(data.load_tables(self.b), lenient=True)
        s = t['세미나'][0]
        self.assertEqual(len(t['세미나']), 1)  # 체크박스만 있는 빈 줄은 건너뜀
        self.assertTrue(s['id'].startswith('s-'))
        self.assertEqual(s['강사진_id'], 'jung-yongtaek')
        self.assertEqual((s['시작일'], s['종료일'], s['상태'], s['공개']), ('2026-11-05', '2026-11-12', '모집중', '예'))
        r = t['회차']
        self.assertEqual([x['세미나_id'] for x in r], [s['id']] * 2)
        self.assertEqual([(x['회차'], x['시간'], x['제목']) for x in r], [('1', '19:30', '1회'), ('2', '19:00', '2회')])
        self.assertEqual(sheet_friendly.PROBLEMS, [])

    def test_mistakes_are_explained_not_fatal(self):
        self.write('공지', [['제목', '본문', '링크', '올린 날', '홈피에 보이기'],
                          ['공지 하나', '본문', 'www.naver.com', '언젠가', '예'],
                          ['', '제목 없는 공지', '', '', '예']])
        t = data.validate(data.load_tables(self.b), lenient=True)
        self.assertEqual([(r['제목'], r['링크_url'], r['게시일']) for r in t['공지']], [('공지 하나', '', '')])
        msgs = ' / '.join(p[3] for p in sheet_friendly.PROBLEMS)
        self.assertIn('https://', msgs)
        self.assertIn('2026-11-05', msgs)
        self.assertIn('제목', msgs)
        self.assertIn('고칠 것', sheet_friendly.check_csv())


if __name__ == '__main__':
    unittest.main()
