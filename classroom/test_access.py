"""HTTP integration tests: state transitions, actual bytes, privilege boundaries."""
import base64
import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from server import make_server


class AccessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = make_server(self.temp.name, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''
        self.csrf = ''
        self.email = 'member@example.test'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def call(self, path, data=None, cookie=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        h = {'Origin': f'http://127.0.0.1:{self.server.server_port}',
             'Content-Type': 'application/json', 'Cookie': self.cookie if cookie is None else cookie}
        h.update(headers or {})
        c.request('GET' if data is None else 'POST', path,
                  None if data is None else json.dumps({'csrf': self.csrf, **data}), h)
        r = c.getresponse()
        code, body, meta = r.status, r.read(), dict(r.getheaders())
        c.close()
        return code, body, meta

    def request(self, path, data, expected=200, **kw):
        code, body, meta = self.call(path, data, **kw)
        self.assertEqual(code, expected, body)
        return json.loads(body), meta

    def verify(self, email):
        c, _ = self.request('/api/apply', {'email': email, 'name': '가상 회원', 'birth': '1990-01-01',
                                         'phone': '01000000000', 'consent': True})
        self.challenge(c['challenge'])

    def challenge(self, challenge):
        mail, _ = self.request('/api/test-mail', {'challenge': challenge})
        return self.request('/api/verify', {'challenge': challenge, 'code': mail['code']})

    def login(self, email):
        # Advance the resend cooldown in test state; keep the real limiter enabled.
        with self.server.trial.connect() as db:
            db.execute('update otps set sent=0 where email=?',(email,))
        c, _ = self.request('/api/otp', {'email': email})
        _, meta = self.challenge(c['challenge'])
        self.cookie = meta['Set-Cookie'].split(';')[0]
        self.csrf = json.loads(self.call('/api/me')[1])['member']['csrf']

    def admin(self):
        self.login('admin.one@example.test')

    def approve(self, email):
        self.request('/api/admin/status', {'email': email, 'status': 'approved', 'matched': True})

    def lesson(self, audience='supporter'):
        # Container fixture used only for HTTP byte authorization (playback uses real ffmpeg fixture).
        payload = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 64
        result, _ = self.request('/api/admin/lessons', {'title': '비공개 시험 강의',
            'audience': audience, 'video': base64.b64encode(payload).decode(), 'material': 'PRIVATE_CANARY_TEST_ONLY'}, 201)
        return result['id']

    def test_unverified_pending_held_suspended_and_anonymous_bytes(self):
        self.admin()
        lesson = self.lesson()
        for url in (f'/media/{lesson}/video', f'/media/{lesson}/material', '/api/lessons'):
            self.assertEqual(self.call(url, cookie='')[0], 403)
        c, _ = self.request('/api/apply', {'email':self.email,'name':'가상 회원','birth':'1990-01-01','phone':'01000000000','consent':True})
        self.request('/api/admin/status', {'email':self.email,'status':'approved','matched':True}, 409)
        self.challenge(c['challenge'])
        self.request('/api/otp', {'email':self.email}, 403)
        self.request('/api/admin/status', {'email':self.email,'status':'held'})
        self.request('/api/otp', {'email':self.email}, 403)
        self.approve(self.email)
        admin_cookie, admin_csrf = self.cookie, self.csrf
        self.login(self.email)
        member_cookie, member_csrf = self.cookie, self.csrf
        self.assertEqual(self.call(f'/media/{lesson}/material')[1], b'PRIVATE_CANARY_TEST_ONLY')
        self.assertEqual(self.call(f'/media/{lesson}/video',headers={'Range':'bytes=0-7'})[0],206)
        self.cookie, self.csrf = admin_cookie, admin_csrf
        self.request('/api/admin/status', {'email':self.email,'status':'suspended'})
        self.cookie, self.csrf = member_cookie, member_csrf
        for url in (f'/media/{lesson}/video', f'/media/{lesson}/material','/api/lessons'):
            self.assertEqual(self.call(url)[0], 403)
        self.request('/api/otp', {'email':self.email},403)

    def test_member_cannot_approve_self_upload_read_members_or_paid_course(self):
        self.verify(self.email)
        self.admin()
        paid = self.lesson('paid_student')
        agit = self.lesson('agit_member')
        self.approve(self.email)
        self.login(self.email)
        self.assertEqual(self.call('/api/admin/members')[0],403)
        self.request('/api/admin/status',{'email':self.email,'status':'approved','matched':True},403)
        self.request('/api/admin/lessons',{'title':'bad'},403)
        self.assertEqual(self.call(f'/media/{paid}/video')[0],403)
        self.assertEqual(self.call(f'/media/{agit}/video')[0],403)
        self.assertEqual(json.loads(self.call('/api/lessons')[1]),[])

    def test_three_member_groups_are_not_interchangeable(self):
        self.admin()
        lessons={a:self.lesson(a) for a in ('supporter','agit_member','paid_student')}
        for audience in lessons:
            email=audience+'@example.test'
            with self.server.trial.connect() as db:
                db.execute("insert into members values (?,?,?,?,?,?,1,'approved','member',?)",
                           (email,'가상 권한시험','1990-01-01','01000000000','trial-2026-10-29',time.time(),audience))
            self.login(email)
            for target,lesson in lessons.items():
                for kind in ('video','material'):
                    self.assertEqual(self.call(f'/media/{lesson}/{kind}')[0],200 if target==audience else 403)

    def test_otp_one_use_expiry_attempt_limit_and_suspension_before_verify(self):
        self.verify(self.email)
        self.admin()
        self.approve(self.email)
        time.sleep(2.01)
        result, _ = self.request('/api/otp',{'email':self.email})
        challenge = result['challenge']
        self.challenge(challenge)
        self.request('/api/verify',{'challenge':challenge,'code':'000000'},400)
        with self.server.trial.connect() as db:
            db.execute('update otps set sent=0 where email=?',(self.email,))
        result, _ = self.request('/api/otp',{'email':self.email})
        challenge = result['challenge']
        for _ in range(5):
            self.request('/api/verify',{'challenge':challenge,'code':'invalid'},400)
        mail,_=self.request('/api/test-mail',{'challenge':challenge})
        self.request('/api/verify',{'challenge':challenge,'code':mail['code']},400)
        with self.server.trial.connect() as db:
            db.execute('update otps set sent=0 where email=?',(self.email,))
        result, _ = self.request('/api/otp',{'email':self.email})
        self.request('/api/admin/status',{'email':self.email,'status':'suspended'})
        mail,_=self.request('/api/test-mail',result)
        self.request('/api/verify',{**result,'code':mail['code']},403)
        with self.server.trial.connect() as db:
            db.execute('update otps set used=0,expires=0 where challenge=?',(result['challenge'],))
        self.request('/api/verify',{**result,'code':mail['code']},400)

    def test_consent_real_email_invalid_date_host_origin_csrf_and_path_boundaries(self):
        p={'email':self.email,'name':'가상 회원','birth':'1990-01-01','phone':'01000000000','consent':True}
        for patch in ({'consent':False},{'birth':'2990-01-01'},{'email':'person@gmail.com'},{'phone':'abc'}):
            self.request('/api/apply',{**p,**patch},400)
        self.request('/api/apply',p,403,headers={'Origin':'https://untrusted.example'})
        self.assertEqual(self.call('/',headers={'Host':'untrusted.example'})[0],403)
        self.admin()
        self.request('/api/admin/status',{'csrf':'wrong'},403)
        for path in ('/../server.py','/trial.sqlite3','/private/trial.sqlite3','/server.py','/.git/config'):
            self.assertEqual(self.call(path)[0],404)
        status, body, meta=self.call('/')
        self.assertIn('noindex',meta['X-Robots-Tag'])
        self.assertEqual(meta['Cache-Control'],'no-store')
        self.assertNotIn(b'PRIVATE_CANARY_TEST_ONLY',body)

    def test_individual_admin_audit_and_range(self):
        self.verify(self.email)
        self.login('admin.two@example.test')
        self.approve(self.email)
        audit=json.loads(self.call('/api/admin/audit')[1])
        self.assertEqual(audit[0]['actor'],'admin.two@example.test')
        lesson=self.lesson()
        self.assertEqual(self.call(f'/media/{lesson}/video',headers={'Range':'bytes=-8'})[0],206)
        self.assertEqual(self.call(f'/media/{lesson}/video',headers={'Range':'bytes=100000-'})[0],416)


if __name__=='__main__':
    unittest.main(verbosity=2)
