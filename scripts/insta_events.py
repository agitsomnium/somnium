"""인스타 글 → 홈페이지 일정 (자동). 키·모델 없이 글의 정해진 꼴만 읽는다.

솜니움 인스타 홍보글은 이렇게 쓴다 — 이 꼴이면 다음 날 아침 달력·프로그램 쪽에 저절로 들어간다.
    [11월 솜니움 북클럽1 | 가까스로-있음]        ← 첫 줄: [달 솜니움 갈래 | 제목]  (갈래: 북클럽·세미나·특강·강좌)
    (소개 글)
    *일시 | 2026년 11월 12·19·26일(목) 저녁 7–9시 · 총 3회
    *장소 | 솜니움 사무실(합정역–상수역 사이) · 온라인 Zoom 병행
    *참가비 | 일반 3만원 · 후원회원 무료
    *신청 | 프로필 링크        ← 주소(https://…)가 있으면 그 주소, 없으면 인스타 글로 연결
시트(또는 연습 자료)에 같은 제목이 이미 있으면 시트가 이긴다 — 자동 줄은 덧붙이지 않는다."""
import re
import unicodedata

HEAD_RE = re.compile(r'^\s*\[\s*(\d{1,2})월\s*솜니움\s*(북클럽|세미나|특강|강좌)\s*\d*\s*\|\s*(.+?)\s*\]', re.M)
FIELD_RE = re.compile(r'^\s*\*\s*(일시|장소|참가비|신청)\s*[|:：]\s*(.+?)\s*$', re.M)
YEAR_RE = re.compile(r'(\d{2}|\d{4})\s*년')
MONTH_RE = re.compile(r'(\d{1,2})\s*월')
STOP_RE = re.compile(r'[(（]|오전|오후|저녁|밤|낮')
TIME_RE = re.compile(r'(오전|오후|저녁|밤|낮)?\s*(\d{1,2})(?::(\d{2}))?\s*(?:시)?\s*[–\-~]\s*\d{1,2}(?::\d{2})?\s*시')
URL_RE = re.compile(r'https?://\S+')


def _key(s):
    s = unicodedata.normalize('NFKC', s or '')
    return re.sub(r'[\s!！?？.,·\-–—「」『』《》<>()\[\]]', '', s)


def _days(when, posted):
    y = YEAR_RE.search(when)
    year = int(y.group(1)) if y else int((posted or '2026')[:4])
    if year < 100:
        year += 2000
    m = MONTH_RE.search(when)
    if not m:
        return []
    month = int(m.group(1))
    rest = when[m.end():]
    stop = STOP_RE.search(rest)
    rest = rest[:stop.start()] if stop else rest
    out = []
    for d in re.findall(r'\d{1,2}', rest):
        d = int(d)
        if 1 <= d <= 31:
            out.append('%04d-%02d-%02d' % (year, month, d))
    return out


def _time(when):
    m = TIME_RE.search(when)
    if not m:
        return ''
    h = int(m.group(2))
    if m.group(1) in ('오후', '저녁', '밤') and h < 12:
        h += 12
    return '%02d:%s' % (h, m.group(3) or '00')


def parse_post(post):
    text = post.get('text') or post.get('caption') or ''
    head = HEAD_RE.search(text)
    if not head:
        return None
    kind, title = head.group(2), head.group(3).strip()
    fields = {k: v for k, v in FIELD_RE.findall(text)}
    when = fields.get('일시', '')
    days = _days(when, post.get('date', ''))
    if not days:
        return None
    body = text[head.end():]
    intro = next((ln.strip() for ln in body.split('\n') if ln.strip() and not ln.strip().startswith(('*', '['))), '')
    url = URL_RE.search(fields.get('신청', ''))
    return {'kind': kind, 'title': title, 'month': head.group(1), 'days': days, 'time': _time(when),
            'place': fields.get('장소', ''), 'fee': fields.get('참가비', ''), 'intro': intro,
            'link': url.group(0) if url else post.get('link', '')}


def merge(tables, posts, today=None):
    """시트에 없는 인스타 일정만 표에 덧붙인다. 덧붙인 개수를 돌려준다."""
    have = {_key(r.get('도서') or r.get('제목')) for r in tables.get('북클럽', [])}
    have |= {_key(r.get('제목')) for r in tables.get('세미나', [])}
    added = 0
    for post in posts or []:
        ev = parse_post(post)
        if not ev or _key(ev['title']) in have:
            continue
        have.add(_key(ev['title']))
        last = ev['days'][-1]
        state = '종료' if today and last < today.isoformat() else '모집중'
        slug = 'ig-' + re.sub(r'[^a-z0-9]', '', (post.get('link', '').rstrip('/').split('/')[-1]).lower())[:20] or 'ig-%d' % added
        intro = ev['intro'] + ((' 참가비 ' + ev['fee'] + '.') if ev['fee'] else '')
        if ev['kind'] == '북클럽':
            tables['북클럽'].append({'id': slug, '제목': '%s월 북클럽' % ev['month'], '도서': ev['title'], '소개': intro,
                                    '날짜': ';'.join(ev['days']), '시간': ev['time'], '장소': ev['place'], '신청_url': ev['link'],
                                    '상태': state, '취소사유': '', '공개': '예', '정렬': '90'})
        else:
            tables['세미나'].append({'id': slug, '제목': ev['title'], '부제': '%s월 %s' % (ev['month'], ev['kind']), '소개': intro,
                                    '상태': state, '시작일': ev['days'][0], '종료일': last, '장소': ev['place'], '강사진_id': '',
                                    '신청_url': ev['link'], '취소사유': '', '공개': '예', '정렬': '90', '참가비': ev['fee'], '참여방법': ''})
            for n, d in enumerate(ev['days'], 1):
                tables['회차'].append({'id': '%s-%d' % (slug, n), '세미나_id': slug, '회차': str(n), '제목': '%d회' % n,
                                      '날짜': d, '시간': ev['time'], '자료_url': '', '공개': '예'})
        added += 1
    return added
