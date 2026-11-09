import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pages import program_page, about_page
from render import shell

class ProgramPriority(unittest.TestCase):
    def test_real_bookclubs_have_one_application_each_before_public_lectures(self):
        books = [dict(id=str(i), 공개='예', 상태='모집중', 제목=name, 신청_url=f'https://example.org/apply/{i}', 날짜='2026-11-10', 시간='19:00') for i, name in enumerate(['가까스로 있음', '이 망할 세상에서 사랑이라니!'])]
        tables = {'북클럽': books, '강사진': [], '세미나': [dict(id='preview', 공개='예', 상태='예고', 제목='작동의 정치')]}
        result = program_page(tables, {}, lambda s: s)
        self.assertLess(result.index('id="bookclubs"'), result.index('id="seminars"'))
        for i in range(2):
            self.assertEqual(result.count(f'href="https://example.org/apply/{i}"'), 1)
        self.assertNotIn('program-signups', result)
        self.assertNotIn('page-intro', result)
        self.assertNotIn('작동의 정치', result)
        self.assertIn('행성적 사유와 신학의 만남', result)
        self.assertIn('HcpmsrS_s7w', result)
        self.assertIn('월 1만 원 후원', result)
        self.assertNotIn('5YT5ias8Qzk', result)

    def test_single_annual_program_menu_and_history_inside_about(self):
        with patch('render.today', return_value=date(2026, 12, 1)):
            result = shell('프로그램', '')
        nav = result.split('aria-label="주요 메뉴">')[1].split('</nav>')[0]
        self.assertEqual(nav.count('/programs/'), 1)
        self.assertIn('2026 강좌·세미나·북클럽', nav)
        self.assertNotIn('12월 프로그램', nav)
        self.assertNotIn('/archive/', nav)
        self.assertNotIn('class="page-navigation"', result)
        about = about_page({'archive.md': '# 지난 프로그램\n2020년 실제 기록'}, lambda text: text)
        self.assertIn('id="past-programs"', about)
        self.assertIn('2020년 실제 기록', about)
        self.assertIn('후원회원 강의 둘러보기', about)
        self.assertIn('/videos/', about)
