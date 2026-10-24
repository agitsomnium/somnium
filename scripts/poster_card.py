"""홈 「이달 프로그램」 카드 — 솜니움 인스타 포스터 시리즈 틀(2026-10-24 확정판)을 그대로 옮긴 것.

틀: 왼쪽 위 미색 딱지 · 오른쪽 위 somnium · 책 색 바탕 · 손글씨 제목(한 낱말만 분홍) · 책 표지 ·
아래 미색 정보띠(큰 날짜 / 요일·시간·장소·참가비 / 이끔이 / QR).
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

# 책 표지에서 뽑은 바탕색(문서 예시). 없으면 쪽빛.
BG = {'이 망할 세상에서 사랑이라니!': '#2B1A33', '가까스로-있음': '#E5484F'}
# 분홍으로 칠할 한 낱말(인스타 포스터와 같게). 없으면 칠하지 않는다.
PINK = {'이 망할 세상에서 사랑이라니!': '사랑'}
# 책 표지 사진(assets/ 안). 파일이 생기면 여기에 적는다.
COVERS = {}
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
    """[11/12, 11/19, 11/26] → '11.12·19·26' (달이 바뀌면 달도 적음)."""
    if not ds:
        return ''
    if len(ds) > 3:  # 여러 주 이어지는 세미나는 처음–끝
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


def _card(kind_tag, title, bg, ds, time, place, fee, leader, url, href, cover):
    when = big_date(ds)
    lines = []
    if ds:
        day = WEEK[ds[0].weekday()] + '요일'
        lines.append(' · '.join(x for x in (day + (' ' + time if time else ''), ('%d회' % len(ds)) if len(ds) > 1 else '') if x))
    if place:
        lines.append(place)
    if fee:
        lines.append(fee)
    cover_html = ('<img class="pc-cover" src="%s" alt="" loading="lazy">' % e(cover)) if cover else ''
    qr = qr_svg(url)
    apply = ''
    if url:
        apply = ('<a class="pc-apply" href="%s" target="_blank" rel="noopener">%s<span>참여 신청</span></a>'
                 % (e(url), qr))
    return (
        '<article class="pc" style="--pc-bg:%s">'
        '<div class="pc-top"><p class="pc-badge">%s</p>'
        '<p class="pc-brand"><span class="pc-som">somnium</span><span>솜니움 기독교정치사회연구소</span></p></div>'
        '<a class="pc-main" href="%s"><h3 class="pc-title">%s</h3>%s</a>'
        '<div class="pc-info"><div class="pc-when">%s%s</div>'
        '<div class="pc-side">%s%s</div></div>'
        '</article>'
        % (e(bg), e(kind_tag), e(href), title, cover_html,
           ('<p class="pc-date">%s</p>' % e(when)) if when else '',
           ''.join('<p>%s</p>' % e(x) for x in lines),
           ('<p class="pc-leader">%s</p>' % e(leader)) if leader else '', apply))


def _from_intro(intro, pat):
    m = re.search(pat, intro or '')
    return m.group(1).strip() if m else ''


def program_cards(tables, base='', today=None):
    today = today or _dt.date.today()
    items = []
    for b in public_rows(tables, '북클럽'):
        if b.get('상태') not in ('모집중', '진행중'):
            continue
        ds = _dates(b.get('날짜'))
        book = b.get('도서') or b.get('제목', '')
        tag = ('%d월 솜니움 북클럽' % ds[0].month) if ds else '솜니움 북클럽'
        intro = b.get('소개', '')
        leader = _from_intro(intro, r'((?:이끔이|진행)\s*[가-힣]{2,4})')
        fee = _from_intro(intro, r'(참가비[^.]*)\.')
        nxt = next((d for d in ds if d >= today), ds[-1] if ds else today)
        items.append((nxt, _card(tag, _title_html(book, PINK.get(book)), BG.get(book, '#23407A'), ds,
                                 b.get('시간', ''), b.get('장소', ''), fee, leader, b.get('신청_url', ''),
                                 '%s/programs/#book-%s' % (base, b.get('id', '')), COVERS.get(b.get('id', '')))))
    fac = {f['id']: f['이름'] for f in public_rows(tables, '강사진')}
    for s in public_rows(tables, '세미나'):
        if s.get('상태') not in ('모집중', '진행중'):
            continue
        sid = s.get('id', '')
        ds = sorted(d for r in public_rows(tables, '회차') if r.get('세미나_id') == sid for d in _dates(r.get('날짜')))
        names = [fac[i] for i in (s.get('강사진_id') or '').split(';') if i in fac]
        times = [r.get('시간') for r in public_rows(tables, '회차') if r.get('세미나_id') == sid and r.get('시간')]
        nxt = next((d for d in ds if d >= today), ds[-1] if ds else today)
        title = s.get('제목', '')
        items.append((nxt, _card('솜니움 세미나', _title_html(title, PINK.get(title)), BG.get(title, '#23407A'), ds,
                                 times[0] if times else '', s.get('장소', ''), s.get('참가비', ''),
                                 ('이끔이 ' + ' · '.join(names)) if names else '', s.get('신청_url', ''),
                                 '%s/seminars/%s/' % (base, e(sid)), COVERS.get(sid))))
    if not items:
        return ''
    items.sort(key=lambda x: x[0])
    return ('<section class="pz-sec band-navy pz-progs" aria-labelledby="pz-progs-h">'
            '<h2 id="pz-progs-h" class="band-h">이달 프로그램</h2>'
            '<div class="pc-grid">' + ''.join(c for _, c in items) + '</div></section>')
