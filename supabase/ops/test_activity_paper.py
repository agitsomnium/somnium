import copy, json, re, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent.parent / 'web'))
from build_activity_paper import build, check, VERSION
from reportCsp import paper_csp

DATA = dict(version=VERSION, org='솜니움', title='2026년도 활동평가', period='2026. 1 – 11', issued='2026. 12', author='대표', audience='이사회',
    office=dict(hours='수', venue='아지트', staff='대표', tasks=['기획'], shift='없음'),
    channels=dict(youtube=dict(url='youtube.com/@x', meta='구독자 1'), instagram=dict(url='instagram.com/x', meta='팔로워 1')),
    programs=[dict(kind='세미나', name='가 </script><b>', date='3월', host='갑', applied=3, mode='대면', inflow='지인', assess=['좋았다'])],
    inflowAgg={'지인': 3}, finance=dict(carryover=10, income=[['후원', 100]], expense=[['임대', 40]], notes=['메모']),
    plan=dict(network=dict(concept='개념', recommend=dict(name='간사', text='글'), benefits=['혜택'], members=[['이름', '소속', '비고']]), lineup=[['1월', '갑', '강의']]), digital=[['홈페이지', '개통']])


class ActivityPaper(unittest.TestCase):
    def test_builds_self_contained_page_with_escaped_data(self):
        body = build(copy.deepcopy(DATA))
        self.assertIn(VERSION, body); self.assertIn("default-src &#x27;none&#x27;", body); self.assertIn("connect-src &#x27;none&#x27;", body)
        self.assertNotIn('REPORT_JSON', body); self.assertNotIn('REPORT_CSP', body)
        self.assertNotRegex(body, r'https?://|src=')  # nothing is fetched from outside
        payload = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', body, re.S).group(1)
        self.assertNotIn('<', payload); self.assertEqual(json.loads(payload)['programs'][0]['name'], '가 </script><b>')

    def test_rejects_mismatched_totals_and_contact_details(self):
        bad = copy.deepcopy(DATA); bad['inflowAgg'] = {'지인': 2}
        with self.assertRaisesRegex(ValueError, 'inflow total'): check(bad)
        bad = copy.deepcopy(DATA); bad['programs'][0]['kind'] = '공동연구 세미나'
        with self.assertRaisesRegex(ValueError, 'kind'): check(bad)
        for leak in ('문의 010-1234-5678', 'someone@example.org'):
            bad = copy.deepcopy(DATA); bad['programs'][0]['assess'] = [leak]
            with self.assertRaisesRegex(ValueError, 'phone number or e-mail'): build(bad)

    def test_viewer_csp_allows_both_fixed_papers(self):
        csp = paper_csp()
        self.assertEqual(csp.count("'sha256-"), 4); self.assertNotIn('unsafe-inline\'; style-src', csp); self.assertNotIn("script-src 'self' 'unsafe", csp)


if __name__ == '__main__': unittest.main()
