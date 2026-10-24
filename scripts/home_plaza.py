"""1안 「달력 광장」 홈 (2026-10-23 확정). 글꼴 B: 제목 검은고딕 · 숫자 Archivo Black · 본문 Pretendard."""
from html import escape as e

from data import public_rows
from extras import (today, collect_events, _shift, _month_range, WEEK,
                    youtube_section, social_strip, accounts_block, social_feeds, fmt_days, pay_bar, news_strip)
import datetime as _dt

POSTERS = {'book-october': 'sonjeol.webp', 'book-november': 'gakkaseuro.webp'}


def _calendar(tables, base, now):
    cur = _dt.date(now.year, now.month, 1)
    dated, ranges, undated = collect_events(tables, base)
    cols = []
    for n, tag in ((1, '다음 달'), (0, '이번 달'), (-1, '지난달')):  # 다가올 일부터
        first = _shift(cur, n)
        lo, hi = _month_range(first)
        rows = []
        for ev in dated:
            if lo <= ev['date'] <= hi:
                meta = WEEK[ev['date'].weekday()] + (' ' + ev['time'] if ev['time'] else '') + ' · ' + ev['kind']
                rows.append((ev['date'], str(ev['date'].day), ev['title'], meta, ev['href'], ev['date'] < now))
        for ev in ranges:
            if ev['start'] <= hi and ev['end'] >= lo:
                big = WEEK[ev['start'].weekday()]
                span = '%d.%d – %d.%d' % (ev['start'].month, ev['start'].day, ev['end'].month, ev['end'].day)
                meta = '매주 · ' + span + (' · ' + ev['place'] if ev.get('place') else '')
                rows.append((max(ev['start'], lo), big, ev['title'], meta, ev['href'], ev['end'] < now))
        rows.sort(key=lambda r: r[0])
        lis = ''.join(
            '<li%s><span class="pz-day num">%s</span><span class="pz-ev"><a href="%s">%s</a><span>%s</span></span></li>'
            % (' class="is-past"' if past else '', e(big), e(href), e(title), e(meta))
            for _, big, title, meta, href, past in rows)
        empty = {'지난달': '이 달에 기록된 모임이 없습니다.', '이번 달': '이번 달 일정을 준비하고 있습니다.',
                 '다음 달': '다음 달 일정이 정해지면 이곳에 올립니다.'}[tag]
        body = '<ul>%s</ul>' % lis if lis else '<p class="pz-empty">%s</p>' % empty
        cols.append('<div class="pz-month%s"><p class="pz-tag">%s</p><h2>%d년 %d월</h2>%s</div>'
                    % (' is-now' if n == 0 else '', tag, first.year, first.month, body))
    soon = ''
    if undated:
        soon = '<p class="pz-soon"><strong>날짜를 정하고 있는 공부</strong> ' + ' · '.join(
            '<a href="%s">%s</a>' % (e(ev['href']), e(ev['title'])) for ev in undated) + '</p>'
    return '<div class="pz-cal">' + ''.join(cols) + '</div>' + soon


def _feature(tables, base):
    seminars = public_rows(tables, '세미나')
    if not seminars:
        return '<p class="pz-empty">진행 중인 세미나 일정을 준비하고 있습니다.</p>'
    live = [s for s in seminars if s.get('상태') in ('진행중', '모집중')]
    s = (live or seminars)[0]
    href = '%s/seminars/%s/' % (base, e(s.get('id', '')))
    fac = {f['id']: f for f in public_rows(tables, '강사진')}
    names = [fac[i.strip()] for i in (s.get('강사진_id') or '').split(';') if i.strip() in fac]
    rows = []
    if s.get('시작일'):
        def md(v):
            y, m, d = v.split('-')
            return '%d.%d' % (int(m), int(d))
        when = md(s['시작일'])
        if s.get('종료일'):
            when += ' – ' + md(s['종료일'])
        rows.append(('언제', e(when)))
    if s.get('장소'):
        rows.append(('어디서', e(s['장소'])))
    if names:
        rows.append(('이끔이', ' · '.join(e(f['이름']) for f in names)))
    if s.get('참가비'):
        rows.append(('참가비', e(s['참가비'])))
    if s.get('참여방법'):
        rows.append(('참여', e(s['참여방법'])))
    if s.get('신청_url'):
        rows.append(('신청', '<a href="%s" target="_blank" rel="noopener">신청하기 ↗</a>' % e(s['신청_url'])))
    dl = ''.join('<dt>%s</dt><dd>%s</dd>' % (k, v) for k, v in rows)
    state = ' · '.join(x for x in (s.get('부제', ''), s.get('상태', '')) if x)
    return ('<div class="pz-feature"><div class="pz-feature-main">'
            '<p class="pz-tag">%s</p><h3>%s</h3><p>%s</p>'
            '<p class="pz-first">처음 오셔도 함께 공부할 수 있습니다. 미리 읽어 올 것과 참여 방법은 <a href="%s/participate/">참여 안내</a>에 있습니다.</p>'
            '<a class="pz-btn-light" href="%s">세미나 자세히 보기</a></div>'
            '<dl class="pz-facts">%s</dl></div>'
            % (e(state), e(s.get('제목', '')), e((s.get('소개') or '').split('\n')[0]), base, href,
               dl or '<dt>일정</dt><dd>운영진 확인 뒤 안내합니다</dd>'))


def _books(tables, base):
    books = public_rows(tables, '북클럽')
    if not books:
        return ''
    cards = []
    for b in books:
        bid = b.get('id', '')
        img = ''
        if bid in POSTERS:
            img = ('<img src="%s/assets/%s" alt="%s 북클럽 포스터" width="864" height="1080" loading="lazy">'
                   % (base, POSTERS[bid], e(b.get('도서', ''))))
        date = fmt_days(b.get('날짜', ''))
        meta = ' · '.join(x for x in (b.get('제목', ''), b.get('상태', ''), date) if x)
        apply = ''
        if b.get('신청_url') and b.get('상태') in ('모집중', '진행중', '예고'):
            apply = ('<p><a class="pz-apply" href="%s" target="_blank" rel="noopener">신청하기 ↗</a></p>'
                     % e(b['신청_url']))
        cards.append('<article class="pz-book"><a href="%s/programs/#book-%s">%s</a><div><p class="pz-tag">%s</p>'
                     '<h3>%s</h3>%s%s</div></article>'
                     % (base, e(bid), img, e(meta), e(b.get('도서', '')),
                        ('<p>%s</p>' % e(b['소개'])) if b.get('소개') else '', apply))
    return ('<section class="pz-sec" aria-labelledby="pz-book-h"><h2 id="pz-book-h" class="pz-kicker">'
            '책에서 시작하는 대화 · 북클럽</h2><div class="pz-books">' + ''.join(cards) + '</div></section>')


def _notices(tables):
    ns = public_rows(tables, '공지')
    if not ns:
        return ''
    items = ''.join('<li><strong>%s</strong>%s%s</li>' % (
        e(n.get('제목', '')), (' — ' + e(n['본문'])) if n.get('본문') else '',
        (' <a href="%s">자세히 ↗</a>' % e(n['링크_url'])) if n.get('링크_url') else '') for n in ns)
    return '<section class="pz-sec pz-notice" aria-label="소식"><h2 class="pz-kicker">소식</h2><ul>%s</ul></section>' % items


def home(tables, base='', videos=None, insta=None):
    now = today()
    out = [
        '<section class="pz-hero" aria-labelledby="pz-h1">',
        '<div><p class="pz-tag">기독교 신앙으로 정치와 사회를 다시 묻는 공부의 광장</p>',
        '<h1 id="pz-h1">%d월,<br>솜니움에서는</h1></div>' % now.month,
        '<p class="pz-lead">다음 달 예고, 이번 달 모임, 지난달 기록을 한 장의 달력으로 봅니다. '
        '기독교와 정치사회 현실을 함께 공부하는 연구소입니다. <a href="%s/about/">솜니움 알아보기 →</a></p>' % base,
        '</section>',
        pay_bar(),
        news_strip(insta or []),
        '<section class="pz-sec pz-study" aria-labelledby="pz-study-h"><h2 id="pz-study-h" class="pz-kicker">이번에 함께할 공부</h2>',
        _feature(tables, base), '</section>',
        '<section id="cal" class="pz-cal-wrap" aria-label="이달의 프로그램">', _calendar(tables, base, now), '</section>',
        _books(tables, base),
        youtube_section(videos or []),
        '<p class="archive-more"><a href="%s/archive/">2017년부터 걸어온 프로그램 보기 →</a></p>' % base,
        _notices(tables),
        social_strip(),
    ]
    return '\n'.join(x for x in out if x)
