"""홈 「이달 프로그램」 카드 (2026-10-24 개정 — 홈피 최적화판).

인스타 포스터 틀(세로 1080×1350)을 그대로 옮기면 빈 공간이 많고 정보 글씨가 작아진다.
그래서 색·손글씨 제목·딱지만 인스타에서 가져오고, 짜임은 1안처럼 «언제·어디서·이끔이·참가비»가
또렷이 읽히는 가로 카드로 만든다. 표지 사진이 있으면 색 칸에 함께 놓는다.
문구는 시트에 적힌 것만 쓴다. 모르면 비워 둔다.
"""
import datetime as _dt
import re
from html import escape as e

from data import public_rows

try:
    import segno
except ImportError:  # QR 없이도 카드는 그린다
    segno = None

# 책 표지에서 뽑은 바탕색. 없으면 쪽빛.
BG = {'이 망할 세상에서 사랑이라니!': '#2B1A33', '가까스로-있음': '#E5484F', '손절사회': '#1B1D22'}
# 분홍으로 칠할 한 낱말(인스타 포스터와 같게)
PINK = {'이 망할 세상에서 사랑이라니!': '사랑'}
# 책 표지(assets/ 안). id 기준
COVERS = {}  # 지금 assets 의 webp 는 표지가 아니라 인스타 포스터라 넣지 않음
WEEK = '월화수목금토일'


def _dates(v):
    out = []
    for p in (v or '').split(';'):
        try:
            out.append(_dt.date.fromisoformat(p.strip()))
        except ValueError:
            pass
    return sorted(out)


def big_date(ds):
    """[11/12, 11/19, 11/26] → '11.12·19·26'. 네 번 넘으면 '9.17–10.29'."""
    if not ds:
        return ''
    if len(ds) > 3:
        return '%d.%d–%d.%d' % (ds[0].month, ds[0].day, ds[-1].month, ds[-1].day)
    parts, prev = [], None
    for d in ds:
        parts.append('%d.%d' % (d.month, d.day) if prev is None or d.month != prev.month else str(d.day))
        prev = d
    return '·'.join(parts)


def qr_svg(url):
    if not segno or not url:
        return ''
    q = segno.make(url, error='m')
    svg = q.svg_inline(scale=1, border=0, dark='#1B1D22', light=None, omitsize=True)
    return svg.replace('<svg ', '<svg class="pc-qr-svg" role="img" aria-label="신청서 QR" ', 1)


def _title_html(title, pink):
    t = e(title)
    if pink and pink in title:
        t = t.replace(e(pink), '<span class="pc-pink">%s</span>' % e(pink), 1)
    return t


def _first_sentence(t):
    t = (t or '').strip().split('\n')[0]
    m = re.match(r'^(.+?[.!?])(\s|$)', t)
    return (m.group(1) if m else t)[:120]


def _from_intro(intro, pat):
    m = re.search(pat, intro or '')
    return m.group(1).strip() if m else ''


def _card(c, base):
    ds = c['dates']
    when_sub = ''
    if ds:
        day = WEEK[ds[0].weekday()] + '요일'
        when_sub = ' · '.join(x for x in (day + (' ' + c['time'] if c['time'] else ''),
                                          ('%d회' % len(ds)) if len(ds) > 1 else '') if x)
    rows = []
    if when_sub:
        rows.append(('언제', when_sub))
    if c['place']:
        rows.append(('어디서', c['place']))
    if c['leader']:
        rows.append(('이끔이', c['leader']))
    if c['fee']:
        rows.append(('참가비', c['fee']))
    dl = ''.join('<dt>%s</dt><dd>%s</dd>' % (k, e(v)) for k, v in rows)
    cover = ('<img class="pc-cover" src="%s/assets/%s" alt="『%s』 표지" loading="lazy">'
             % (base, e(c['cover']), e(c['plain_title']))) if c['cover'] else ''
    acts = ''
    if c['url']:
        acts += '<a class="pc-btn" href="%s" target="_blank" rel="noopener">참여 신청 ↗</a>' % e(c['url'])
    acts += '<a class="pc-more" href="%s">자세히 보기</a>' % e(c['href'])
    qr = qr_svg(c['url'])
    return (
        '<article class="pc%s" style="--pc-bg:%s">'
        '<a class="pc-head" href="%s"><p class="pc-badge">%s</p>'
        '<h3 class="pc-title">%s</h3>%s<p class="pc-date">%s</p></a>'
        '<div class="pc-body">'
        '%s'
        '<dl class="pc-facts">%s</dl>'
        '<div class="pc-acts">%s%s</div>'
        '</div></article>'
        % (' has-cover' if cover else '', e(c['bg']), e(c['href']), e(c['tag']), c['title'], cover,
           e(big_date(ds)),
           ('<p class="pc-lead">%s</p>' % e(c['lead'])) if c['lead'] else '',
           dl, acts, ('<span class="pc-qr" title="폰으로 찍어 신청">%s</span>' % qr) if qr else ''))


def program_cards(tables, base='', today=None):
    today = today or _dt.date.today()
    items = []
    for b in public_rows(tables, '북클럽'):
        if b.get('상태') not in ('모집중', '진행중'):
            continue
        ds = _dates(b.get('날짜'))
        book = b.get('도서') or b.get('제목', '')
        intro = b.get('소개', '')
        items.append(dict(
            tag=(('%d월 북클럽' % ds[0].month) if ds else '북클럽') + ' · ' + b.get('상태', ''),
            title=_title_html(book, PINK.get(book)), plain_title=book, bg=BG.get(book, '#23407A'), dates=ds,
            time=b.get('시간', ''), place=b.get('장소', ''),
            fee=_from_intro(intro, r'참가비\s*([^.]*)\.'),
            leader=_from_intro(intro, r'(?:이끔이|진행)\s*([가-힣]{2,4})'),
            lead=_first_sentence(intro), url=b.get('신청_url', ''),
            href='%s/programs/#book-%s' % (base, b.get('id', '')), cover=COVERS.get(b.get('id', ''), '')))
    fac = {f['id']: f['이름'] for f in public_rows(tables, '강사진')}
    ses = public_rows(tables, '회차')
    for s in public_rows(tables, '세미나'):
        if s.get('상태') not in ('모집중', '진행중'):
            continue
        sid = s.get('id', '')
        ds = sorted(d for r in ses if r.get('세미나_id') == sid for d in _dates(r.get('날짜')))
        names = [fac[i] for i in (s.get('강사진_id') or '').split(';') if i in fac]
        times = [r.get('시간') for r in ses if r.get('세미나_id') == sid and r.get('시간')]
        title = s.get('제목', '')
        items.append(dict(
            tag='세미나 · ' + s.get('상태', ''), title=_title_html(title, PINK.get(title)), plain_title=title,
            bg=BG.get(title, '#23407A'), dates=ds, time=times[0] if times else '', place=s.get('장소', ''),
            fee=s.get('참가비', ''), leader=' · '.join(names), lead=_first_sentence(s.get('소개', '')),
            url=s.get('신청_url', ''), href='%s/seminars/%s/' % (base, sid), cover=COVERS.get(sid, '')))
    if not items:
        return ''

    def key(c):
        nxt = next((d for d in c['dates'] if d >= today), None)
        return (nxt is None, nxt or today)
    items.sort(key=key)
    return ('<section class="pz-sec pz-progs" aria-labelledby="pz-progs-h">'
            '<h2 id="pz-progs-h" class="band-h">이달 프로그램</h2>'
            '<div class="pc-grid">' + ''.join(_card(c, base) for c in items) + '</div></section>')
