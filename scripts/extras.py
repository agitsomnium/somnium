"""홈페이지 보강 블록: 월별 일정, 유튜브, SNS, 계좌, 이사진 틀."""
import datetime as _dt
import json
import os
from html import escape as e
from pathlib import Path

from data import public_rows
from fetch_social import is_short_video

ROOT = Path(__file__).resolve().parents[1]
KST = _dt.timezone(_dt.timedelta(hours=9))
WEEK = '월화수목금토일'


CONFIG_OVERRIDES = {}  # 빌드 때 시트의 계좌·연락 탭으로 채운다


def site_config():
    p = ROOT / 'config' / 'site.json'
    try:
        cfg = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cfg = {}
    for k, v in CONFIG_OVERRIDES.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] = dict(cfg[k], **v)
        else:
            cfg[k] = v
    return cfg


def today():
    raw = os.environ.get('SITE_TODAY', '').strip()
    if raw:
        return _dt.date.fromisoformat(raw)
    return _dt.datetime.now(KST).date()


def fmt_days(v):
    """'2026-11-12;2026-11-19' → '11.12 · 11.19' (해가 다르면 해까지)."""
    ds = [x for x in (_d(p) for p in (v or '').split(';')) if x]
    if not ds:
        return (v or '').strip()
    head = '%d.%d.%d' % (ds[0].year, ds[0].month, ds[0].day)
    return ' · '.join([head] + ['%d.%d' % (d.month, d.day) for d in ds[1:]])


def _d(s):
    try:
        return _dt.date.fromisoformat((s or '').strip())
    except ValueError:
        return None


def _shift(first, n):
    m = first.month - 1 + n
    return _dt.date(first.year + m // 12, m % 12 + 1, 1)


def _month_range(first):
    return first, _shift(first, 1) - _dt.timedelta(days=1)


def _label(d):
    return '%d.%d (%s)' % (d.month, d.day, WEEK[d.weekday()])


def collect_events(tables, base=''):
    """날짜가 있는 일정 모으기. 날짜 없는 예정은 따로."""
    seminars = {s.get('id'): s for s in public_rows(tables, '세미나')}
    dated, ranges, undated = [], [], []
    with_sessions = set()
    for r in public_rows(tables, '회차'):
        d = _d(r.get('날짜'))
        s = seminars.get(r.get('세미나_id'))
        if not d or not s:
            continue
        with_sessions.add(s.get('id'))
        title = '%s · %s' % (s.get('제목', ''), r.get('제목', '') or '%s회' % r.get('회차', ''))
        dated.append({'date': d, 'time': r.get('시간', ''), 'title': title, 'kind': '세미나',
                      'href': '%s/seminars/%s/' % (base, s.get('id'))})
    for s in seminars.values():
        if s.get('상태') == '취소':
            continue
        a, b = _d(s.get('시작일')), _d(s.get('종료일'))
        href = '%s/seminars/%s/' % (base, s.get('id'))
        if a and s.get('id') not in with_sessions:
            ranges.append({'start': a, 'end': b or a, 'title': s.get('제목', ''), 'kind': '세미나',
                           'href': href, 'place': s.get('장소', '')})
        elif not a and s.get('상태') in ('예고', '모집중'):
            undated.append({'title': s.get('제목', ''), 'kind': '세미나', 'href': href, 'state': s.get('상태', '')})
    for bk in public_rows(tables, '북클럽'):
        if bk.get('상태') == '취소':
            continue
        days = [x for x in (_d(v) for v in (bk.get('날짜') or '').split(';')) if x]
        title = '%s 『%s』' % (bk.get('제목', ''), bk.get('도서', '')) if bk.get('도서') else bk.get('제목', '')
        href = '%s/programs/#book-%s' % (base, bk.get('id'))
        if days:
            for n, d in enumerate(days, 1):
                t = title + (' (%d/%d)' % (n, len(days)) if len(days) > 1 else '')
                dated.append({'date': d, 'time': bk.get('시간', ''), 'title': t, 'kind': '북클럽', 'href': href})
        elif bk.get('상태') in ('예고', '모집중', '진행중'):
            undated.append({'title': title, 'kind': '북클럽', 'href': href, 'state': bk.get('상태', '')})
    return dated, ranges, undated


def month_calendar(tables, base='', now=None):
    now = now or today()
    cur = _dt.date(now.year, now.month, 1)
    dated, ranges, undated = collect_events(tables, base)
    cols = []
    for n, name in ((-1, '지난달'), (0, '이번 달'), (1, '다음 달')):
        first = _shift(cur, n)
        lo, hi = _month_range(first)
        items = []
        for ev in dated:
            if lo <= ev['date'] <= hi:
                when = _label(ev['date']) + (' ' + ev['time'] if ev['time'] else '')
                items.append((ev['date'], when, ev))
        for ev in ranges:
            if ev['start'] <= hi and ev['end'] >= lo:
                if ev['start'] == ev['end']:
                    when = _label(ev['start'])
                else:
                    when = '%d.%d – %d.%d' % (ev['start'].month, ev['start'].day, ev['end'].month, ev['end'].day)
                items.append((max(ev['start'], lo), when, ev))
        items.sort(key=lambda x: x[0])
        lis = []
        for _, when, ev in items:
            past = ' class="is-past"' if (ev.get('date') or ev.get('end')) < now else ''
            lis.append('<li%s><time>%s</time><a href="%s">%s</a><span class="cal-kind">%s</span></li>'
                       % (past, e(when), e(ev['href']), e(ev['title']), e(ev['kind'])))
        empty = {'지난달': '이 달에 기록된 모임이 없습니다.', '이번 달': '이번 달 일정을 준비하고 있습니다.',
                 '다음 달': '다음 달 일정이 정해지면 이곳에 올립니다.'}[name]
        body = '<ul class="cal-list">' + ''.join(lis) + '</ul>' if lis else '<p class="cal-empty">%s</p>' % empty
        cur_attr = ' aria-current="date"' if n == 0 else ''
        cols.append('<div class="cal-col%s"%s><h3><span>%s</span>%d년 %d월</h3>%s</div>'
                    % (' is-now' if n == 0 else '', cur_attr, name, first.year, first.month, body))
    out = ['<section class="month-cal" aria-labelledby="cal-title">',
           '<div class="section-heading"><h2 id="cal-title">이달의 프로그램</h2>'
           '<p>지난달 기록과 이번 달, 다음 달 일정을 한눈에 봅니다.</p></div>',
           '<div class="cal-grid">' + ''.join(cols) + '</div>']
    if undated:
        out.append('<div class="cal-soon"><h3>날짜를 정하고 있는 공부</h3><ul>')
        for ev in undated:
            out.append('<li><a href="%s">%s</a> <span class="cal-kind">%s · %s</span></li>'
                       % (e(ev['href']), e(ev['title']), e(ev['kind']), e(ev['state'])))
        out.append('</ul></div>')
    out.append('</section>')
    return '\n'.join(out)


def load_videos(data_dir):
    p = Path(data_dir) / 'youtube.json'
    try:
        rows = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    clean = []
    for r in rows if isinstance(rows, list) else []:
        vid = str(r.get('id', ''))
        if len(vid) == 11 and all(c.isalnum() or c in '-_' for c in vid):
            clean.append({'id': vid, 'title': str(r.get('title', '')), 'published': str(r.get('published', ''))[:10]})
    return clean


def _first_gen_row(base):
    """1기 강좌 채널에서 강의 영상 4편(질의응답 빼고)을 홈에 보인다."""
    import re as _re
    try:
        from videos_page import load_catalog
        rows = [r for r in load_catalog([]) if r.get('channel') == 'series' and '(강의)' in r.get('title', '')][:4]
    except Exception:
        return ''
    if not rows:
        return ''
    cards = []
    for v in rows:
        t = _re.sub(r'\s*\[한국기독학생운동사를 돌아보며\].*$', '', v['title']).replace('(강의)', '·')
        t = _re.sub(r'\s+', ' ', t).strip()
        cards.append('<a class="yt-card" href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener">'
                     '<img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" alt="" width="480" height="360" loading="lazy">'
                     '<strong>%s</strong></a>' % (e(v['id']), e(v['id']), e(t)))
    return ('<div class="yt-firstgen"><p class="yt-firstgen-h">솜니움 1기 강좌 · 한국기독학생운동사를 돌아보며 '
            '<a href="%s/videos/first-gen/">18편 모두 보기 →</a></p><div class="yt-grid yt-grid-4">%s</div></div>'
            % (base, ''.join(cards)))


def youtube_section(videos, limit=6, base=''):
    cfg = site_config().get('youtube') or {}
    url = cfg.get('url', '')
    out = ['<section class="yt-section band-navy" aria-labelledby="yt-title">',
           '<div class="section-heading"><h2 id="yt-title" class="band-h">유튜브</h2></div>']
    if videos:
        out.append('<div class="yt-grid">')
        for v in videos[:limit]:
            watch = 'https://www.youtube.com/watch?v=' + v['id']
            thumb = 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % v['id']
            date = ('<time>%s</time>' % e(v['published'].replace('-', '.'))) if v['published'] else ''
            out.append('<a class="yt-card" href="%s" target="_blank" rel="noopener">'
                       '<img src="%s" alt="" width="480" height="360" loading="lazy">'
                       '<strong>%s</strong>%s</a>' % (e(watch), e(thumb), e(v['title']), date))
        out.append('</div>')
    if url:
        out.append('<p class="yt-links"><a class="button yt-button" href="%s" target="_blank" rel="noopener">유튜브 채널 바로가기 ↗</a></p>' % e(url))
    out.append(_first_gen_row(base))
    for m in (site_config().get('youtube_more') or []):
        if not m.get('url'):
            continue
        out.append('<a class="yt-series" href="%s" target="_blank" rel="noopener"><span class="yt-series-tag">%s</span>'
                   '<strong>%s</strong><span class="yt-series-desc">%s</span><span class="yt-series-go">유튜브에서 보기 ↗</span></a>'
                   % (e(m['url']), e(m.get('구분', '')), e(m.get('이름', '')), e(m.get('설명', ''))))
    out.append('</section>')
    return '\n'.join(out)


def _social_items(cfg):
    items = [('youtube', '유튜브', cfg.get('youtube') or {})]
    for m in cfg.get('youtube_more') or []:
        items.append(('youtube', '유튜브 · ' + (m.get('구분') or '이전 채널'), {'url': m.get('url', ''), '이름': m.get('이름', '')}))
    items += [('instagram', '인스타그램', cfg.get('instagram') or {}), ('facebook', '페이스북', cfg.get('facebook') or {})]
    return items


def social_strip():
    cfg = site_config()
    links = []
    for key, label, c in _social_items(cfg):
        if c.get('url'):
            links.append('<a class="social-link social-%s" href="%s" target="_blank" rel="noopener"><span>%s</span><strong>%s</strong></a>'
                         % (key, e(c['url']), e(label), e(c.get('이름', ''))))
    if not links:
        return ''
    return ('<section class="social-strip" aria-labelledby="social-title"><h2 id="social-title">솜니움 소식 받아보기</h2>'
            '<div class="social-grid">' + ''.join(links) + '</div></section>')


def footer_social():
    cfg = site_config()
    out = []
    for key, label, c in _social_items(cfg):
        if c.get('url'):
            out.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (e(c['url']), e(label)))
    return ''.join(out)


def accounts_block(heading='후원·참가비 계좌', compact=False):
    cfg = site_config()
    accts = cfg.get('accounts') or []
    if not accts:
        return ''
    cards = []
    for a in accts:
        num = a.get('번호', '')
        cards.append('<article class="acct-card"><p class="acct-use">%s <span>%s</span></p>'
                     '<p class="acct-num"><span>%s</span> <strong>%s</strong></p>'
                     '<p class="acct-holder">예금주 %s</p>%s'
                     '<button type="button" class="acct-copy" data-copy="%s">계좌번호 복사</button></article>'
                     % (e(a.get('용도', '')), e(a.get('설명', '')), e(a.get('은행', '')), e(num),
                        e(a.get('예금주', '')), ('<p class="acct-hint">%s</p>' % e(a['안내'])) if a.get('안내') else '', e(num)))
    cms = cfg.get('cms_url', '')
    extra = ''
    if cms:
        extra = '<p class="acct-cms"><a class="button" href="%s" target="_blank" rel="noopener">CMS 정기후원 신청 ↗</a></p>' % e(cms)
    note = '<p class="acct-note">송금 뒤 <a href="mailto:%s">%s</a>로 이름과 용도를 알려 주세요.</p>' % (
        e(cfg.get('email', '')), e(cfg.get('email', '')))
    cls = 'acct-block compact' if compact else 'acct-block'
    return ('<section class="%s" aria-labelledby="acct-title"><h2 id="acct-title">%s</h2>'
            '<div class="acct-grid">%s</div>%s%s</section>' % (cls, e(heading), ''.join(cards), extra, note))


def pay_bar():
    """홈 맨 위 «참가비·후원 계좌» 띠 — 한눈에 보이고 바로 복사."""
    accts = site_config().get('accounts') or []
    if not accts:
        return ''
    rows = ''.join(
        '<div class="pay-row"><p class="pay-use">%s<span>%s</span></p>'
        '<p class="pay-num"><span>%s</span> <strong>%s</strong></p>'
        '<button type="button" class="acct-copy pay-copy" data-copy="%s">복사</button>'
        '<p class="pay-holder">예금주 %s%s</p></div>'
        % (e(a.get('용도', '')), (' · ' + e(a['설명'])) if a.get('설명') else '', e(a.get('은행', '')), e(a.get('번호', '')),
           e(a.get('번호', '')), e(a.get('예금주', '')), (' · ' + e(a['안내'])) if a.get('안내') else '')
        for a in accts)
    return ('<section class="pay-bar" aria-labelledby="pay-h"><h2 id="pay-h">참가비 · 후원 계좌</h2>'
            '<div class="pay-rows">%s</div></section>' % rows)


def news_strip(insta, limit=6):
    """홈 맨 앞 «새 소식» — 인스타 홍보 포스터를 크게. 같은 홍보를 여러 번 올렸으면 최신 하나만."""
    import re as _re
    if not insta:
        return ''
    ig = site_config().get('instagram') or {}
    seen, cards = set(), []
    for p in insta:
        if is_short_video(p):
            continue
        text = (p.get('text') or p.get('caption') or '').strip()
        first = text.split('\n', 1)[0].strip()
        m = _re.match(r'^\[\s*(?:(\d{1,2})월\s*)?(.*?)\s*(?:\|\s*(.+?))?\s*\]', first)
        if m and m.group(3):
            kind, title = _re.sub(r'\d+$', '', m.group(2)).strip(), m.group(3).strip()
        elif m:
            after = first[m.end():].strip()
            kind, title = m.group(2).strip(), (_re.split(r'\s[:：]\s', after)[0].strip() if after else m.group(2).strip())
        else:
            kind, title = '', first[:40]
        kind = _re.sub(r'^솜니움\s*', '', kind)
        key = _re.sub(r'\W', '', title)
        if key in seen:
            continue
        seen.add(key)
        d = p.get('date', '')
        cards.append('<a class="news-card" href="%s" target="_blank" rel="noopener">'
                     '<img src="%s" alt="%s 포스터" loading="lazy" width="432" height="540">'
                     '<span class="news-kind">%s</span><strong>%s</strong>%s</a>'
                     % (e(p['link']), e(p['image']), e(title), e(kind or '소식'), e(title),
                        ('<time datetime="%s">%s 올림</time>' % (e(d), e(d[5:].replace('-', '.')))) if d else ''))
        if len(cards) >= limit:
            break
    if not cards:
        return ''
    return ('<section class="news-strip" aria-labelledby="news-h"><div class="news-head"><h2 id="news-h">따끈한 소식</h2>'
            '<a href="%s" target="_blank" rel="noopener">인스타그램에서 더 보기 ↗</a></div>'
            '<div class="news-row">%s</div></section>' % (e(ig.get('url', '')), ''.join(cards)))


def board_frame():
    seats = site_config().get('board') or []
    if not seats:
        return ''
    cells = []
    for s in seats:
        name = s.get('이름', '').strip()
        cells.append('<div class="board-seat"><span>%s</span><strong>%s</strong></div>'
                     % (e(s.get('자리', '')), e(name) if name else '<em>명단 정리 중</em>'))
    return '<div class="board-grid">' + ''.join(cells) + '</div>'


def load_instagram(data_dir, limit=6):
    p = Path(data_dir) / 'instagram.json'
    try:
        rows = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [r for r in rows if isinstance(r, dict) and str(r.get('link', '')).startswith('https://www.instagram.com/')
            and str(r.get('image', '')).startswith('https://') and not is_short_video(r)][:limit]


def social_feeds(insta):
    """인스타 최신 글 6개 + 페이스북 페이지 타임라인. 둘 다 없으면 빈 문자열."""
    from urllib.parse import quote
    cfg = site_config()
    ig = cfg.get('instagram') or {}
    fb = cfg.get('facebook') or {}
    cols = []
    if insta:
        tiles = ''.join('<a class="ig-tile" href="%s" target="_blank" rel="noopener"><img src="%s" alt="%s" loading="lazy" width="320" height="320"></a>'
                        % (e(p['link']), e(p['image']), e(p.get('caption') or '솜니움 인스타그램 게시물')) for p in insta)
        cols.append('<div class="feed-col"><h3>인스타그램 <a href="%s" target="_blank" rel="noopener">%s ↗</a></h3><div class="ig-grid">%s</div></div>'
                    % (e(ig.get('url', '')), e(ig.get('이름', '')), tiles))
    if not cols:
        return ''
    return '<div class="feed-wrap">' + ''.join(cols) + '</div>'
