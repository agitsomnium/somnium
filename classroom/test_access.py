"""HTTP integration tests: state transitions, actual bytes, privilege boundaries."""
import base64
import http.client
import json
import tempfile
import threading
import time
import unittest
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

    def verify(self, email, intent="supporter"):
        c, _ = self.request('/api/apply', {'email': email, 'name': '가상 회원', 'birth': '1990-01-01',
                                         'phone': '01000000000', 'consent': True, 'intent': intent})
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
        self.request('/api/admin/supporter', {'email': email, 'qualified': True, 'minimum_confirmed': True})

    def lesson(self, era='archive', series=''):
        # Container fixture used only for HTTP byte authorization (playback uses real ffmpeg fixture).
        payload = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 64
        result, _ = self.request('/api/admin/lessons', {'title': '비공개 시험 강의',
            'era': era, 'series_id':series, 'video': base64.b64encode(payload).decode(), 'material': 'PRIVATE_CANARY_TEST_ONLY'}, 201)
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

    def test_supporter_includes_current_and_future_but_cannot_manage_members(self):
        self.verify(self.email)
        self.admin()
        paid = self.lesson('current','capitalism')
        future = self.lesson('future','2027')
        self.approve(self.email)
        self.login(self.email)
        self.assertEqual(self.call('/api/admin/members')[0],403)
        self.request('/api/admin/supporter',{'email':self.email,'qualified':True,'minimum_confirmed':True},403)
        self.request('/api/admin/lessons',{'title':'bad'},403)
        self.assertEqual(self.call(f'/media/{paid}/video')[0],200)
        self.assertEqual(self.call(f'/media/{future}/material')[0],200)
        self.assertEqual(len(json.loads(self.call('/api/lessons')[1])),2)

    def test_purchase_verification_does_not_grant_any_lecture(self):
        self.verify(self.email,'purchase')
        self.login(self.email)
        self.assertEqual(json.loads(self.call('/api/lessons')[1]),[])
        self.assertFalse(json.loads(self.call('/api/me')[1])['member']['supporter'])

    def test_application_cannot_set_own_role_status_or_supporter_qualification(self):
        c,_=self.request('/api/apply',{'email':self.email,'name':'가상 회원','birth':'1990-01-01',
            'phone':'01000000000','consent':True,'intent':'purchase','role':'admin','status':'approved',
            'qualified':True,'audience':'supporter'})
        self.challenge(c['challenge'])
        self.login(self.email)
        member=json.loads(self.call('/api/me')[1])['member']
        self.assertEqual(member['role'],'member')
        self.assertFalse(member['supporter'])

    def test_catalog_has_no_private_paths_and_missing_era_upload_is_rejected(self):
        self.admin()
        self.lesson('current')
        listing=json.loads(self.call('/api/catalog',cookie='')[1])
        self.assertNotIn('video',listing[0])
        self.assertNotIn('material',listing[0])
        self.assertFalse(listing[0]['accessible'])
        self.request('/api/admin/lessons',{'title':'old client','audience':'paid_student'},400)

    def test_historical_series_cannot_be_purchased_even_with_current_lecture(self):
        self.admin()
        self.lesson('archive','mixed')
        self.lesson('current','mixed')
        self.verify(self.email,'purchase')
        self.login(self.email)
        self.request('/api/orders',{'target_type':'series','target_id':'mixed'},400)

    def test_test_mail_notification_is_never_shown_to_other_buyer(self):
        self.admin()
        lesson=self.lesson('current')
        self.verify(self.email,'purchase')
        self.login(self.email)
        o,_=self.request('/api/orders',{'target_type':'lesson','target_id':lesson},201)
        self.admin()
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True})
        self.verify('other@example.test','purchase')
        self.login('other@example.test')
        self.assertEqual(json.loads(self.call('/api/notifications')[1]),[])

    def test_single_order_manual_confirmation_is_idempotent_and_scoped(self):
        self.admin()
        lesson=self.lesson('current','capitalism')
        sibling=self.lesson('current','capitalism')
        archive=self.lesson('archive')
        self.verify(self.email,'purchase')
        self.login(self.email)
        buyer=(self.cookie,self.csrf)
        o,_=self.request('/api/orders',{'target_type':'lesson','target_id':lesson},201)
        dup,_=self.request('/api/orders',{'target_type':'lesson','target_id':lesson})
        self.assertEqual(o['id'],dup['id'])
        self.assertEqual(self.call(f'/media/{lesson}/video')[0],403)
        self.request('/api/orders',{'target_type':'lesson','target_id':archive},400)
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True},403)
        self.admin()
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed'},409)
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True})
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True})
        self.cookie,self.csrf=buyer
        self.assertEqual(self.call(f'/media/{lesson}/video')[0],200)
        self.assertEqual(self.call(f'/media/{sibling}/video')[0],403)
        self.assertEqual(self.call(f'/media/{archive}/video')[0],403)
        self.assertEqual(len(json.loads(self.call('/api/notifications')[1])),1)
        self.request('/api/orders/cancel',{'id':o['id']},409)

    def test_series_access_supporter_expiry_and_purchase_revocation(self):
        self.verify(self.email,'purchase')
        self.admin()
        archive=self.lesson('archive')
        a=self.lesson('current','capitalism')
        b=self.lesson('current','capitalism')
        other=self.lesson('future','next')
        self.approve(self.email)
        self.login(self.email)
        buyer=(self.cookie,self.csrf)
        o,_=self.request('/api/orders',{'target_type':'series','target_id':'capitalism'},201)
        self.admin()
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True})
        self.request('/api/admin/supporter',{'email':self.email,'qualified':False,'hold':True})
        self.assertEqual(self.call(f'/media/{a}/video',cookie=buyer[0])[0],200)
        self.assertEqual(self.call(f'/media/{archive}/video',cookie=buyer[0])[0],403)
        self.request('/api/admin/supporter',{'email':self.email,'qualified':False})
        from commerce import setup
        with self.server.trial.connect() as db:
            setup(db)
        self.cookie,self.csrf=buyer
        self.assertEqual(self.call(f'/media/{archive}/video')[0],403)
        for lesson in (a,b):
            self.assertEqual(self.call(f'/media/{lesson}/video')[0],200)
        self.assertEqual(self.call(f'/media/{other}/video')[0],403)
        self.admin()
        self.request('/api/admin/orders',{'id':o['id'],'status':'cancelled'})
        self.cookie,self.csrf=buyer
        self.assertEqual(self.call(f'/media/{a}/material')[0],403)
        self.assertEqual(self.call(f'/media/{b}/video',headers={'Range':'bytes=0-3'})[0],403)

    def test_buyer_cannot_cancel_or_see_another_buyers_order(self):
        self.admin()
        lesson=self.lesson('current')
        self.verify('one@example.test','purchase')
        self.login('one@example.test')
        o,_=self.request('/api/orders',{'target_type':'lesson','target_id':lesson},201)
        self.verify('two@example.test','purchase')
        self.login('two@example.test')
        self.assertEqual(json.loads(self.call('/api/orders')[1]),[])
        self.request('/api/orders/cancel',{'id':o['id']},409)

    def test_account_suspension_blocks_purchased_bytes_until_explicit_resume(self):
        self.verify(self.email,'purchase')
        self.admin()
        lesson=self.lesson('current')
        self.login(self.email)
        buyer=(self.cookie,self.csrf)
        o,_=self.request('/api/orders',{'target_type':'lesson','target_id':lesson},201)
        self.admin()
        self.request('/api/admin/orders',{'id':o['id'],'status':'confirmed','matched':True})
        self.request('/api/admin/account',{'email':self.email,'status':'suspended'})
        self.cookie,self.csrf=buyer
        self.assertEqual(self.call(f'/media/{lesson}/video')[0],403)
        self.admin()
        self.request('/api/admin/account',{'email':self.email,'status':'approved'})
        self.login(self.email)
        self.assertEqual(self.call(f'/media/{lesson}/video')[0],200)
        self.assertFalse(json.loads(self.call('/api/me')[1])['member']['supporter'])

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
