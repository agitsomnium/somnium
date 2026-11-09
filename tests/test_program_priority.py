import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pages import program_page
from render import shell

class ProgramPriority(unittest.TestCase):
    def test_current_applications_precede_previews_and_archive(self):
        books = [dict(id=str(i), 공개='예', 상태='모집중', 제목=name, 신청_url=f'https://example.org/apply/{i}', 날짜='2026-11-10', 시간='19:00') for i, name in enumerate(['가까스로 있음', '이 망할 세상에서 사랑이라니!'])]
        tables = {'북클럽': books, '강사진': [], '세미나': [dict(id='preview', 공개='예', 상태='예고', 제목='작동의 정치'), dict(id='past', 공개='예', 상태='종료', 제목='지난 세미나') ]}
        result = program_page(tables, {}, lambda s: s)
        self.assertLess(result.index('id="bookclubs"'), result.index('id="seminars"'))
        overview = result.split('<div class="book-listing">')[0]
        for i in range(2):
            self.assertIn(f'href="https://example.org/apply/{i}"', overview)
        self.assertNotIn('<h3><a', overview)
        self.assertNotIn('작동의 정치', result)
        self.assertNotIn('지난 세미나', result)
        self.assertIn('행성적 사유와 신학의 만남', result)
        self.assertIn('HcpmsrS_s7w', result)
        self.assertIn('후원회원 강의 안내', result)
        self.assertNotIn('5YT5ias8Qzk', result)

    def test_menu_uses_build_month_and_application_anchor(self):
        with patch('render.today', return_value=date(2026, 12, 1)):
            result = shell('프로그램', '')
        self.assertIn('href="/programs/#bookclubs">12월 프로그램</a>', result)
