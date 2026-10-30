"""Synthetic manual-transfer orders and independent supporter access.

No amounts, account numbers, PG calls, actual transfers, or outbound emails.
"""
import secrets
import time


def setup(db):
    columns = {r['name'] for r in db.execute('pragma table_info(lessons)')}
    for name, declaration in {
        'series_id': "text not null default ''",
        'era': "text not null default 'archive'",
        'supporter_access': "text not null default 'included'",
        'purchasable': 'integer not null default 0',
    }.items():
        if name not in columns:
            db.execute(f'alter table lessons add column {name} {declaration}')
    db.executescript('''
      create table if not exists supporters (
        email text primary key, qualified integer not null default 0,
        checked_at real, checked_by text);
      create table if not exists orders (
        id text primary key, email text not null, target_type text not null,
        target_id text not null, status text not null default 'awaiting',
        created_at real not null, confirmed_at real, confirmed_by text,
        check(target_type in ('lesson','series')),
        check(status in ('awaiting','confirmed','cancelled')));
      create unique index if not exists order_active_target
        on orders(email,target_type,target_id) where status != 'cancelled';
      create table if not exists notifications (
        order_id text primary key, email text not null, body text not null, created_at real not null);
    ''')
    if 'review_state' not in {r['name'] for r in db.execute('pragma table_info(supporters)')}:
        db.execute("alter table supporters add column review_state text not null default 'pending'")
    # Preserve yesterday's already-approved synthetic supporters; never override a withdrawal.
    db.execute('''insert or ignore into supporters(email,qualified,checked_at,checked_by)
        select email,1,?,'legacy-trial' from members
        where role='member' and status='approved' and audience='supporter' ''', (time.time(),))
    db.execute("update supporters set review_state='qualified' where qualified=1")
    # User decision, 2026-10-30: qualified supporters also get current and 2027 lectures.
    db.execute("update lessons set supporter_access='included' where supporter_access='undecided'")


def active(member):
    return bool(member and member['verified'] and member['status'] == 'approved')


def is_supporter(db, email):
    row = db.execute('select qualified from supporters where email=?', (email,)).fetchone()
    return bool(row and row['qualified'])


def supporter_review(db, email):
    row=db.execute('select review_state from supporters where email=?', (email,)).fetchone()
    return row['review_state'] if row else 'pending'


def allowed(db, member, lesson):
    if not active(member) or not lesson or not lesson['published']:
        return False
    if member['role'] == 'admin':
        return True
    if lesson['supporter_access'] == 'included' and is_supporter(db, member['email']):
        return True
    # Historical lectures cannot be sold or unlocked through a purchase, even with a forged order.
    if lesson['era'] == 'archive':
        return False
    return bool(db.execute('''select 1 from orders where email=? and status='confirmed'
      and ((target_type='lesson' and target_id=?)
        or (target_type='series' and target_id=? and target_id!='')) limit 1''',
      (member['email'], lesson['id'], lesson['series_id'])).fetchone())


def target_rows(db, kind, target):
    if not isinstance(target,str) or len(target)>100:
        return []
    if kind == 'lesson':
        rows = db.execute('select * from lessons where id=?', (target,)).fetchall()
    elif kind == 'series' and target:
        rows = db.execute('select * from lessons where series_id=?', (target,)).fetchall()
    else:
        return []
    if not rows or any(not r['published'] or not r['purchasable'] or r['era'] == 'archive' for r in rows):
        return []
    return rows


def get(handler, db, member, path):
    if path == '/api/catalog':
        rows = db.execute('select * from lessons where published=1 order by era,id').fetchall()
        handler.reply(200, [{k:r[k] for k in ('id','title','series_id','era','supporter_access','purchasable')}
            | {'accessible':allowed(db,member,r)} for r in rows])
        return True
    if path in ('/api/orders', '/api/notifications', '/api/admin/orders'):
        if not active(member):
            handler.reply(403, {'error':'로그인이 필요합니다.'})
            return True
        if path == '/api/admin/orders':
            if not handler.admin(member):
                return True
            rows=db.execute('''select o.*,m.name from orders o join members m on m.email=o.email
                               order by created_at desc''').fetchall()
        elif path == '/api/orders':
            rows=db.execute('select * from orders where email=? order by created_at desc', (member['email'],)).fetchall()
        else:
            rows=db.execute('select * from notifications where email=? order by created_at desc', (member['email'],)).fetchall()
        handler.reply(200, [dict(r) for r in rows])
        return True
    return False


def post(handler, db, member, path, p):
    if path not in ('/api/orders','/api/orders/cancel','/api/admin/orders','/api/admin/supporter','/api/admin/account'):
        return False
    if not active(member):
        handler.reply(403, {'error':'로그인 상태를 확인해 주세요.'})
        return True
    if path == '/api/orders':
        kind,target=p.get('target_type'),p.get('target_id')
        if not target_rows(db,kind,target):
            handler.reply(400, {'error':'구매 시험 대상이 아닙니다. 이전 강의는 후원회원 전용입니다.'})
            return True
        existing=db.execute("select id from orders where email=? and target_type=? and target_id=? and status!='cancelled'",
                            (member['email'],kind,target)).fetchone()
        if existing:
            handler.reply(200, {'id':existing['id'],'duplicate':True})
            return True
        oid=secrets.token_urlsafe(18)
        db.execute('insert into orders(id,email,target_type,target_id,created_at) values (?,?,?,?,?)',
                   (oid,member['email'],kind,target,time.time()))
        handler.reply(201, {'id':oid,'message':'시험 신청을 접수했습니다. 실제 입금하지 마세요.'})
        return True
    if path == '/api/orders/cancel':
        row=db.execute('select * from orders where id=? and email=?', (p.get('id'),member['email'])).fetchone()
        if not row or row['status']!='awaiting':
            handler.reply(409, {'error':'대기 중인 본인 신청만 취소할 수 있습니다.'})
            return True
        db.execute("update orders set status='cancelled' where id=?", (row['id'],))
        handler.reply(200, {'message':'시험 신청을 취소했습니다.'})
        return True
    if not handler.admin(member):
        return True
    if path == '/api/admin/account':
        row=db.execute("select * from members where email=? and role='member'", (p.get('email'),)).fetchone()
        status=p.get('status')
        if not row or status not in ('approved','suspended') or (status=='approved' and not row['verified']):
            handler.reply(409, {'error':'이메일 확인과 계정 상태를 확인해 주세요.'})
            return True
        db.execute('update members set status=? where email=?', (status,row['email']))
        if status=='suspended':
            db.execute('delete from sessions where email=?', (row['email'],))
        db.execute('insert into audit values (?,?,?,?)', (time.time(),member['email'],'account_'+status,row['email']))
        handler.reply(200, {'message':'계정 상태를 변경했습니다. 후원·구매 자격은 별도로 관리합니다.'})
        return True
    if path == '/api/admin/supporter':
        row=db.execute("select * from members where email=? and role='member'", (p.get('email'),)).fetchone()
        qualified=p.get('qualified')
        if not row or type(qualified) is not bool or not row['verified']:
            handler.reply(409, {'error':'이메일 확인과 대상 회원을 확인해 주세요.'})
            return True
        if qualified and p.get('minimum_confirmed') is not True:
            handler.reply(409, {'error':'한빛누리에서 월 1만 원 이상 후원 여부를 확인해 주세요.'})
            return True
        review='qualified' if qualified else ('held' if p.get('hold') is True else 'withdrawn')
        db.execute('''insert into supporters(email,qualified,checked_at,checked_by,review_state) values (?,?,?,?,?)
          on conflict(email) do update set qualified=excluded.qualified,checked_at=excluded.checked_at,
          checked_by=excluded.checked_by,review_state=excluded.review_state''',
          (row['email'],int(qualified),time.time(),member['email'],review))
        if qualified and row['status'] in ('pending','held'):
            db.execute("update members set status='approved' where email=?", (row['email'],))
        db.execute('insert into audit values (?,?,?,?)',
                   (time.time(),member['email'],'supporter_'+review,row['email']))
        handler.reply(200, {'message':'후원 자격을 변경했습니다. 구매 수강권은 별도로 유지됩니다.'})
        return True
    row=db.execute('select * from orders where id=?', (p.get('id'),)).fetchone()
    new=p.get('status')
    if not row or new not in ('confirmed','cancelled'):
        handler.reply(400, {'error':'신청과 처리 상태를 확인해 주세요.'})
        return True
    if row['status']==new:
        handler.reply(200, {'message':'이미 처리된 시험 신청입니다.','duplicate':True})
        return True
    buyer=db.execute('select * from members where email=?', (row['email'],)).fetchone()
    if new=='confirmed' and (row['status']!='awaiting' or p.get('matched') is not True
        or not active(buyer) or not target_rows(db,row['target_type'],row['target_id'])):
        handler.reply(409, {'error':'유효한 신청·회원·시험 입금 확인이 필요합니다.'})
        return True
    db.execute('update orders set status=?,confirmed_at=?,confirmed_by=? where id=?',
               (new,time.time(),member['email'],row['id']))
    if new=='confirmed':
        db.execute('insert or ignore into notifications values (?,?,?,?)',
          (row['id'],row['email'],'[발송하지 않은 시험 안내] 수강 권한이 열렸습니다. 로그인 후 나의 강의실에서 확인하세요. 원본 영상 공유 링크는 보내지 않습니다.',time.time()))
    db.execute('insert into audit values (?,?,?,?)',
               (time.time(),member['email'],'order_'+new,row['id']))
    handler.reply(200, {'message':'시험 입금 확인·수강권 부여 완료' if new=='confirmed' else '수강권을 회수했습니다. 실제 환불은 처리하지 않습니다.'})
    return True
