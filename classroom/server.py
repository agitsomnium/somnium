"""Loopback-only, synthetic-data classroom trial. Never deploy this test adapter.

No SMTP, external model, Hub member data, or public YouTube integration.
Production must replace SQLite/mailbox with an organization-owned service.
"""
import base64
import datetime as dt
import hashlib
import json
import mimetypes
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import commerce
from backup_trial import verified_manifest

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
POLICY = 'trial-2026-10-29'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Trial:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        restored = verified_manifest(self.folder)
        self.db = self.folder / 'trial.sqlite3'
        with self.connect() as db:
            db.executescript('''
            create table if not exists members (
              email text primary key, name text not null, birth text not null,
              phone text not null, consent_version text not null, consent_at real not null,
              verified integer not null default 0, status text not null default 'pending',
              role text not null default 'member', audience text not null default 'supporter');
            create table if not exists otps (
              challenge text primary key, email text not null, purpose text not null,
              code_hash text not null, expires real not null, attempts integer not null default 0,
              used integer not null default 0, sent real not null);
            create table if not exists sessions (
              token_hash text primary key, email text not null, expires real not null, csrf text not null);
            create table if not exists lessons (
              id text primary key, title text not null, audience text not null,
              published integer not null default 0, video text not null, material text not null);
            create table if not exists audit (
              at real not null, actor text not null, action text not null, target text not null);
            ''')
            for email in ('admin.one@example.test', 'admin.two@example.test'):
                db.execute("insert or ignore into members values (?,?,?,?,?,?,1,'approved','admin','supporter')",
                           (email, '시험 관리자', '1990-01-01', '01000000000', POLICY, time.time()))
            commerce.setup(db)
        if restored is not None:
            # Preserve restore provenance, then treat this as live mutable state.
            # Otherwise the next legitimate DB edit would make every later backup fail.
            (self.folder / 'backup-manifest.json').rename(
                self.folder / ('restored-origin-' + secrets.token_hex(8) + '.json'))
        self.mailbox = {}  # test mailbox is process-local; codes are never written to logs

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def issue(self, db, email, purpose):
        last = db.execute('select max(sent) from otps where email=?', (email,)).fetchone()[0]
        if last and time.time() - last < 2:
            raise ValueError('잠시 후 다시 요청해 주세요.')
        db.execute('update otps set used=1 where email=? and purpose=?', (email, purpose))
        challenge, code = secrets.token_urlsafe(24), f'{secrets.randbelow(1000000):06}'
        now = time.time()
        db.execute('insert into otps values (?,?,?,?,?,0,0,?)',
                   (challenge, email, purpose, digest(challenge + code), now + 300, now))
        self.mailbox[challenge] = {'code': code, 'email': email, 'purpose': purpose}
        return challenge

    def member(self, db, token):
        return db.execute('''select m.*,s.csrf from sessions s join members m on m.email=s.email
          where s.token_hash=? and s.expires>?''', (digest(token), time.time())).fetchone()

    def allowed(self, db, member, lesson):
        return commerce.allowed(db, member, lesson)


class Handler(BaseHTTPRequestHandler):
    server_version = 'SomniumTrial'

    def log_message(self, *_):
        pass  # no URLs, form values, email addresses, cookies, or OTPs in access logs

    @property
    def trial(self):
        return self.server.trial

    def reply(self, status, data, mime='application/json; charset=utf-8', headers=None):
        # A successful HTTP response must never precede the durable transaction.
        writing = getattr(self, '_writing', None)
        if writing is not None:
            writing.commit()
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.send_response(status)
        for k, v in {
            'Content-Type': mime, 'Content-Length': str(len(data)), 'Cache-Control': 'no-store',
            'X-Robots-Tag': 'noindex, nofollow, noarchive', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; "
            "font-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            **(headers or {})
        }.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def boundary(self):
        host = self.headers.get('Host', '')
        expected = f'127.0.0.1:{self.server.server_port}'
        if host != expected or self.client_address[0] != '127.0.0.1':
            self.reply(403, {'error': '로컬 시험 주소로만 접근할 수 있습니다.'})
            return False
        if self.command == 'POST' and self.headers.get('Origin') != 'http://' + expected:
            self.reply(403, {'error': '출처가 일치하지 않습니다.'})
            return False
        return True

    def token(self):
        try:
            c = SimpleCookie(self.headers.get('Cookie', ''))
            return c['trial_session'].value if 'trial_session' in c else ''
        except Exception:
            return ''

    def do_GET(self):
        if not self.boundary():
            return
        path = urlsplit(self.path).path
        if path == '/':
            return self.reply(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        static = {'/app.js': ROOT / 'app.js', '/trial.css': ROOT / 'trial.css',
                  '/brand.css': REPO / 'assets/site.css', '/tokens.css': REPO / 'assets/tokens.css',
                  '/fonts-display.css': REPO / 'assets/fonts-display.css'}
        if re.fullmatch(r'/fonts/(?:display/)?[a-zA-Z0-9_.-]+\.woff2', path):
            static[path] = REPO / 'assets' / path.lstrip('/')
        if path in static and static[path].is_file():
            return self.reply(200, static[path].read_bytes(), mimetypes.guess_type(str(static[path]))[0] or 'application/octet-stream')
        if path == '/robots.txt':
            return self.reply(200, 'User-agent: *\nDisallow: /\n', 'text/plain')
        with self.trial.connect() as db:
            member = self.trial.member(db, self.token())
            if commerce.get(self, db, member, path):
                return
            if path == '/api/me':
                return self.reply(200, {'member': ({k: member[k] for k in ('email', 'name', 'status', 'role', 'csrf')}
                    | {'supporter':commerce.is_supporter(db,member['email']), 'supporter_review':commerce.supporter_review(db,member['email'])}) if member else None})
            if path == '/api/lessons':
                if not member or member['status'] != 'approved' or not member['verified']:
                    return self.reply(403, {'error': '승인된 회원만 이용할 수 있습니다.'})
                rows = db.execute('select * from lessons order by rowid desc').fetchall()
                return self.reply(200, [{k:r[k] for k in ('id','title','era','series_id')} for r in rows if self.trial.allowed(db, member, r)])
            if path == '/api/admin/members':
                if not self.admin(member):
                    return
                return self.reply(200, [dict(r) | {'supporter':commerce.is_supporter(db,r['email']),
                    'supporter_review':commerce.supporter_review(db,r['email'])} for r in db.execute('select email,name,birth,phone,verified,status,consent_version,consent_at from members where role=\'member\'')])
            if path == '/api/admin/audit':
                if not self.admin(member):
                    return
                return self.reply(200, [dict(r) for r in db.execute('select * from audit order by at desc limit 30')])
            if path == '/api/admin/lessons':
                if not self.admin(member):
                    return
                return self.reply(200, [dict(r) for r in db.execute(
                    'select id,title,era,series_id,published,description,position,series_title from lessons order by era,series_id,position,id')])
            match = re.fullmatch(r'/media/([a-zA-Z0-9_-]+)/(video|material)', path)
            if match:
                lesson = db.execute('select * from lessons where id=?', (match[1],)).fetchone()
                if not self.trial.allowed(db, member, lesson):
                    return self.reply(403, {'error': '이 자료를 이용할 권한이 없습니다.'})
                file = self.trial.folder / lesson[match[2]]
                if not file.is_file():
                    return self.reply(404, {'error': '파일이 없습니다.'})
                data = file.read_bytes()
                mime = 'video/mp4' if match[2] == 'video' else 'text/plain; charset=utf-8'
                headers = {'Accept-Ranges': 'bytes'}
                if match[2] == 'material':
                    headers['Content-Disposition'] = 'attachment; filename="somnium-trial-notes.txt"'
                requested = self.headers.get('Range')
                if requested:
                    m = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                    if not m or not (m[1] or m[2]):
                        return self.reply(416, b'', headers={'Content-Range': f'bytes */{len(data)}'})
                    start = int(m[1]) if m[1] else max(0, len(data) - int(m[2]))
                    end = min(int(m[2]), len(data)-1) if m[1] and m[2] else len(data)-1
                    if start > end or start >= len(data):
                        return self.reply(416, b'', headers={'Content-Range': f'bytes */{len(data)}'})
                    headers['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
                    return self.reply(206, data[start:end+1], mime, headers)
                return self.reply(200, data, mime, headers)
        self.reply(404, {'error': '찾을 수 없습니다.'})

    def admin(self, member):
        if not member or member['role'] != 'admin' or member['status'] != 'approved':
            self.reply(403, {'error': '관리자 권한이 필요합니다.'})
            return False
        return True

    def do_POST(self):
        if not self.boundary():
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 15_000_000 or self.headers.get_content_type() != 'application/json':
                return self.reply(400, {'error': '요청 형식 또는 크기를 확인해 주세요.'})
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('요청을 확인해 주세요.')
            text_fields = ('id','email','status','target_id','target_type','challenge','code',
                           'title','birth','phone','name','series_id','series_title','description','material','intent')
            if any(k in payload and not isinstance(payload[k],str) for k in text_fields):
                raise ValueError('문자 입력 확인')
            with self.trial.connect() as db:
                # Serialize read/check/write transitions (OTP reuse, duplicate orders,
                # cancellation vs confirmation). Read the actor only after acquiring it.
                db.execute('begin immediate')
                self._writing = db
                try:
                    self.post(db, urlsplit(self.path).path, payload)
                finally:
                    self._writing = None
        except (ValueError, KeyError, TypeError, sqlite3.IntegrityError):
            self.reply(400, {'error': '입력과 처리 상태를 확인해 주세요.'})

    def post(self, db, path, p):
        member = self.trial.member(db, self.token())
        if path in ('/api/apply', '/api/otp', '/api/resend-verification'):
            email = str(p.get('email', '')).strip().lower()
            if not re.fullmatch(r'[a-z0-9._+-]{1,60}@example\.test', email):
                raise ValueError('가상 주소만 허용')
            if path == '/api/apply':
                birth = dt.date.fromisoformat(p['birth'])
                if birth > dt.date.today() or birth.year < 1900 or p.get('consent') is not True:
                    raise ValueError('동의와 날짜 확인')
                name, phone = str(p.get('name', '')).strip(), re.sub(r'[- ]', '', str(p.get('phone', '')))
                if not 2 <= len(name) <= 40 or not re.fullmatch(r'010\d{8}', phone):
                    raise ValueError('필수 항목 확인')
                existing = db.execute('select * from members where email=?', (email,)).fetchone()
                if existing:
                    return self.reply(409, {'error': '이미 신청한 주소입니다. 로그인 또는 관리자 문의를 이용해 주세요.'})
                intent=p.get('intent','supporter')
                if intent not in ('supporter','purchase'):
                    raise ValueError('신청 목적 확인')
                db.execute('insert into members(email,name,birth,phone,consent_version,consent_at,audience) values (?,?,?,?,?,?,?)',
                           (email, name, p['birth'], phone, POLICY, time.time(),intent))
                challenge = self.trial.issue(db, email, 'verify')
            elif path == '/api/resend-verification':
                row = db.execute('select * from members where email=?', (email,)).fetchone()
                if not row or row['verified'] or row['status'] == 'suspended':
                    return self.reply(409, {'error': '신청·이메일 확인 상태를 확인해 주세요.'})
                challenge = self.trial.issue(db, email, 'verify')
            else:
                row = db.execute('select * from members where email=?', (email,)).fetchone()
                if not row or not row['verified'] or row['status'] != 'approved':
                    return self.reply(403, {'error': '이메일 확인과 관리자 승인이 필요합니다.'})
                challenge = self.trial.issue(db, email, 'login')
            return self.reply(200, {'challenge': challenge})
        if path == '/api/test-mail':
            # Explicit local test adapter. Never expose on a hosted environment.
            mail = self.trial.mailbox.get(str(p.get('challenge', '')))
            return self.reply(200 if mail else 404, mail or {'error': '시험 메일 없음'})
        if path == '/api/verify':
            challenge, code = str(p.get('challenge', '')), str(p.get('code', ''))
            row = db.execute('select * from otps where challenge=?', (challenge,)).fetchone()
            if not row or row['used'] or row['attempts'] >= 5 or row['expires'] < time.time():
                return self.reply(400, {'error': '인증번호가 만료되었거나 사용할 수 없습니다.'})
            db.execute('update otps set attempts=attempts+1 where challenge=?', (challenge,))
            if not secrets.compare_digest(row['code_hash'], digest(challenge + code)):
                return self.reply(400, {'error': '인증번호가 일치하지 않습니다.'})
            db.execute('update otps set used=1 where challenge=?', (challenge,))
            self.trial.mailbox.pop(challenge, None)
            if row['purpose'] == 'verify':
                db.execute('update members set verified=1 where email=?', (row['email'],))
                db.execute("update members set status='approved' where email=? and audience='purchase' and status='pending'", (row['email'],))
                return self.reply(200, {'message': '이메일을 확인했습니다. 강좌 구매 신청자는 로그인할 수 있으며, 후원 강의는 관리자 자격 확인 후 열립니다.'})
            current = db.execute('select * from members where email=?', (row['email'],)).fetchone()
            if current['status'] != 'approved' or not current['verified']:
                return self.reply(403, {'error': '이용 권한이 없습니다.'})
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
            db.execute('insert into sessions values (?,?,?,?)', (digest(token), row['email'], time.time()+3600, csrf))
            return self.reply(200, {'message': '로그인했습니다.'}, headers={
                'Set-Cookie': f'trial_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'})
        if not member or not secrets.compare_digest(member['csrf'], str(p.get('csrf', ''))):
            return self.reply(403, {'error': '로그인 상태를 다시 확인해 주세요.'})
        if path == '/api/logout':
            db.execute('delete from sessions where token_hash=?', (digest(self.token()),))
            return self.reply(200, {}, headers={'Set-Cookie': 'trial_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        if commerce.post(self, db, member, path, p):
            return
        if not self.admin(member):
            return
        if path == '/api/admin/lesson-details':
            # Purchase scope is immutable here. Changing an era or series must not
            # silently move a lecture across a prior purchase's authorization boundary.
            if set(p)-{'csrf','id','title','description','position'}:
                raise ValueError('수정 항목 확인')
            row=db.execute('select id from lessons where id=?',(p.get('id'),)).fetchone()
            title=str(p.get('title','')).strip()
            description=str(p.get('description','')).strip()
            position=p.get('position')
            if not row or not 1<=len(title)<=100 or len(description)>1200 or type(position) is not int or not 1<=position<=999:
                raise ValueError('강의 정보 확인')
            db.execute('update lessons set title=?,description=?,position=? where id=?',(title,description,position,row['id']))
            db.execute('insert into audit values (?,?,?,?)',(time.time(),member['email'],'lesson_updated',row['id']))
            return self.reply(200, {'message':'강의 소개와 순서를 저장했습니다. 기존 신청 명세는 유지됩니다.'})
        if path == '/api/admin/lesson-publication':
            lesson_id, published = p.get('id'), p.get('published')
            row = db.execute('select id from lessons where id=?', (lesson_id,)).fetchone()
            if not row or type(published) is not bool:
                return self.reply(400, {'error': '강의와 표시 상태를 확인해 주세요.'})
            db.execute('update lessons set published=? where id=?', (int(published), lesson_id))
            db.execute('insert into audit values (?,?,?,?)',
                       (time.time(), member['email'], 'lesson_published' if published else 'lesson_hidden', lesson_id))
            return self.reply(200, {'message': '회원 강의 목록에 표시했습니다.' if published else '강의를 숨겼습니다. 영상·자료 접근도 차단됩니다.'})
        if path == '/api/admin/status':
            status, email = p.get('status'), p.get('email')
            if status not in ('approved', 'held', 'suspended'):
                raise ValueError('상태 확인')
            row = db.execute("select * from members where email=? and role='member'", (email,)).fetchone()
            if not row or (status == 'approved' and (not row['verified'] or p.get('matched') is not True)):
                return self.reply(409, {'error': '이메일 확인 및 한빛누리 수동 대조 확인이 필요합니다.'})
            db.execute('update members set status=? where email=?', (status, email))
            if status == 'approved':
                db.execute('''insert into supporters(email,qualified,checked_at,checked_by) values (?,1,?,?) on conflict(email) do update set
                  qualified=1,checked_at=excluded.checked_at,checked_by=excluded.checked_by''',
                  (email,time.time(),member['email']))
            if status != 'approved':
                db.execute('delete from sessions where email=?', (email,))
            db.execute('insert into audit values (?,?,?,?)', (time.time(), member['email'], status, email))
            return self.reply(200, {'message': '처리했습니다.'})
        if path == '/api/admin/lessons':
            title = str(p.get('title', '')).strip()
            era=p.get('era')
            published=p.get('published', True)
            series=str(p.get('series_id','')).strip()
            series_title=str(p.get('series_title','')).strip()
            description=str(p.get('description','')).strip()
            position=p.get('position',1)
            if len(series_title)>100 or len(description)>1200 or type(position) is not int or not 1<=position<=999:
                raise ValueError('강의 소개 확인')
            if not series and series_title:
                existing=db.execute('select series_id from lessons where series_title=? and series_id!=\'\' limit 1',(series_title,)).fetchone()
                series=existing['series_id'] if existing else secrets.token_hex(8)
            if series:
                existing=db.execute('select era,series_title from lessons where series_id=? limit 1',(series,)).fetchone()
                if existing and existing['era']!=era:
                    raise ValueError('자료 구분이 다른 시리즈')
                if existing:
                    series_title=existing['series_title'] or series_title
            if 'audience' in p or type(published) is not bool or not title or len(title) > 100 or era not in ('archive','current','future') or not re.fullmatch(r'[a-z0-9-]{0,60}',series):
                raise ValueError('강의 정보 확인')
            video = base64.b64decode(p['video'], validate=True)
            material = str(p['material']).encode()
            if len(video) > 10_000_000 or len(video) < 16 or b'ftyp' not in video[:32] or len(material) > 100_000:
                raise ValueError('시험 MP4/자료 확인')
            lesson_id = secrets.token_urlsafe(18)
            video_name, material_name = lesson_id + '.mp4', lesson_id + '.txt'
            (self.trial.folder / video_name).write_bytes(video)
            (self.trial.folder / material_name).write_bytes(material)
            db.execute('''insert into lessons(id,title,audience,published,video,material,series_id,era,supporter_access,purchasable,description,position,series_title)
              values (?,?,'supporter',?,?,?,?,?,?,?,?,?,?)''',
              (lesson_id,title,int(published),video_name,material_name,series,era,'included',int(era!='archive'),description,position,series_title))
            db.execute('insert into audit values (?,?,?,?)', (time.time(), member['email'], 'lesson_created', lesson_id))
            return self.reply(201, {'id': lesson_id})
        self.reply(404, {'error': '찾을 수 없습니다.'})


def make_server(folder, port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.trial = Trial(folder)
    return server


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.state, args.port)
    print(f'가상 데이터 전용 · http://127.0.0.1:{server.server_port} · 외부 배포 금지', flush=True)
    server.serve_forever()
