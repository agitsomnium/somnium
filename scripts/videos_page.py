"""유튜브 쪽. data/catalog/youtube.json(누적 목록)과 data/live/youtube.json(최근 영상)을 합쳐
최근 올라온 순서로 한 줄에 놓는다. 같은 시리즈·같은 강사 영상은 대표 카드 하나로 묶고,
카드를 누르면 /videos/<묶음>/ 쪽에서 그 시리즈 영상을 차례대로 본다.
갈래를 바꾸려면 GROUPS 만 고친다. 날짜는 data/catalog/ytdates.json(영상 id → 올린 날)에서 채운다."""
import json
import re
from html import escape as e
from pathlib import Path

from extras import site_config

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'data' / 'catalog' / 'youtube.json'
DATES = ROOT / 'data' / 'catalog' / 'ytdates.json'

# (시리즈 이름, 한 줄 설명, 묶는 방식, 제목 낱말들)
#   묶는 방식 'one' = 시리즈 전체를 카드 하나로 / 'per' = 같은 강사끼리만 카드 하나로(강사가 다르면 따로)
GROUPS = [
    ('현대 자본주의 이해하기 · 2026 공동연구 세미나', '시즌1 강의와 대화', 'one', ['현대 자본주의 이해하기', '자본주의 세미나', '지대추구', '기술 봉건']),
    ('행성적 사유와 신학의 만남 · 2026 여름 세미나', '정용택·이일청·권지성·손민석·김정형', 'per', ['행성적', 'UN은 하나가', '시온주의']),
    ('스피노자의 삶과 철학과 신학 · 2026 특강', '조현진(단국대)', 'one', ['스피노자']),
    ('연구자 초대 · 2026', '연구자의 지금 공부를 함께 듣습니다', 'per', ['퀴어 그리스도인', 'AI와 악의 평범성', '비인간종', '가치 포획']),
    ('주디스 버틀러의 사유 횡단하기 · 2026 봄 세미나', '발제와 토론', 'one', ['버틀러 횡단']),
    ('특강·북토크 · 2026', '', 'per', ['기호학의 이해', '종교적인 것의 귀환', '페미니즘 설교집']),
    ('포스트모던 사상과 신학의 만남 · 2025 가을 세미나', '이상철(한신대)', 'one', ['지젝', '바디우', '데리다', '레비나스', '벤야민', '니체', '포스트모던']),
    ('요즘(?) 페미니즘 산책하기 · 2025 여름 세미나', '최순양', 'one', ['브라이도티', '사라 아메드', '젠더트러블', '누스바움']),
    ('니클라스 루만과 공동체 · 정성훈 강의', '정성훈', 'one', ['루만', '공동체이론']),
    ('정치×문화×종교 · 2025 봄 세미나', '손민석·엄태빈', 'one', ['정치X문화X종교', '찰스 테일러', '존 카푸토', '후지타', '김보명', '권명아', '시우']),
    ('솜니움 북클럽 · 2025~', '매달 한 권', 'one', ['북클럽', '성서와 동성애', '김진호목사님', '운둔기계', '은둔기계']),
    ('솜니움 이야기', '1기 대표에게 듣는 솜니움의 시작', 'one', ['Q.', '1기 세미나', '감사패']),
]
SERIES_RE = re.compile(r'\]\s*(\d+)([AB]?)-(\d)')
NUM_RE = re.compile(r'\((\d+)(?:-(\d+))?\)')
LECT_RE = re.compile(r'([가-힣]{2,4})\s*(?:교수|선생님|목사님)')


def _clean(rows):
    out = []
    for r in rows if isinstance(rows, list) else []:
        vid = str(r.get('id', ''))
        if len(vid) == 11 and all(c.isalnum() or c in '-_' for c in vid):
            out.append({'id': vid, 'title': str(r.get('title', '')), 'channel': str(r.get('channel', 'main')),
                        'published': str(r.get('published', ''))[:10]})
    return out


def load_catalog(live=None):
    try:
        rows = _clean(json.loads(CATALOG.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        rows = []
    try:
        dates = json.loads(DATES.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        dates = {}
    known = {r['id'] for r in rows}
    fresh = [v for v in _clean(live or []) if v['id'] not in known]
    rows = fresh + rows
    n = len(rows)
    for i, r in enumerate(rows):
        r['published'] = r['published'] or str(dates.get(r['id'], ''))[:10]
        r['_order'] = n - i  # 날짜가 없으면 목록 순서(위가 최근)를 쓴다
    return rows


def _sortkey(v):
    return (v.get('published') or '', v.get('_order', 0))


def _thumb(vid):
    return ('<img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" alt="" width="480" height="360" loading="lazy">' % e(vid))


def _date(v):
    d = v.get('published') or ''
    return '<time datetime="%s">%s</time>' % (e(d), e(d.replace('-', '.'))) if d else ''


def _card(v):
    return ('<a class="yt-card" href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener">%s'
            '<strong>%s</strong>%s</a>' % (e(v['id']), _thumb(v['id']), e(v['title']), _date(v)))


def _group_of(title):
    for i, g in enumerate(GROUPS):
        if any(k in title for k in g[3]):
            return i
    return None


def _episode(v):
    m = SERIES_RE.search(v['title'])
    if m:
        return (int(m.group(1)), m.group(2), int(m.group(3)))
    m = NUM_RE.search(v['title'])
    if m:
        return (int(m.group(1)), '', int(m.group(2) or 0))
    return None


def _in_order(videos):
    """시리즈 안 차례: 제목의 회차 번호가 있으면 그것, 없으면 올린 날 순."""
    return sorted(videos, key=lambda v: (_episode(v) or (999, '', 0), _sortkey(v)))


def _bundles(rows, series_cfg):
    """카드 단위 묶음 목록. 각 묶음 = {'slug','name','desc','lecturer','videos'}"""
    main = [r for r in rows if r['channel'] != 'series' and 'Somnium' not in r['channel']]
    first_gen = [r for r in rows if r not in main]
    buckets = {}
    for r in main:
        gi = _group_of(r['title'])
        if gi is None:
            key = ('v', r['id'])
            lect = ''
        else:
            mode = GROUPS[gi][2]
            m = LECT_RE.search(r['title'])
            lect = m.group(1) if m else ''
            key = ('g', gi) if mode == 'one' else (('g', gi, lect) if lect else ('v', r['id']))
        b = buckets.setdefault(key, {'group': gi, 'lecturer': lect, 'videos': []})
        b['videos'].append(r)
    out = []
    for key, b in buckets.items():
        vids = b['videos']
        if len(vids) == 1:
            out.append({'single': vids[0], 'videos': vids})
            continue
        name, desc = GROUPS[b['group']][0], GROUPS[b['group']][1]
        if GROUPS[b['group']][2] == 'per':
            desc = b['lecturer']
        ordered = _in_order(vids)
        out.append({'slug': ordered[0]['id'], 'name': name, 'desc': desc, 'videos': ordered})
    if first_gen:
        out.append({'slug': 'first-gen', 'name': series_cfg.get('이름', '한국기독학생운동사를 돌아보며'),
                    'tag': series_cfg.get('구분', ''), 'desc': series_cfg.get('설명', ''),
                    'url': series_cfg.get('url', ''), 'videos': sorted(first_gen, key=lambda v: _episode(v) or (99, '', 0))})
    for b in out:
        b['latest'] = max(_sortkey(v) for v in b['videos'])
    out.sort(key=lambda b: b['latest'], reverse=True)
    return out


def _span(videos):
    ds = sorted(v['published'] for v in videos if v.get('published'))
    if not ds:
        return ''
    a, z = ds[0][:7].replace('-', '.'), ds[-1][:7].replace('-', '.')
    return a if a == z else '%s – %s' % (a, z)


def _series_card(b, base):
    first = b['videos'][0]
    sub = ' · '.join(x for x in (b.get('desc') if b.get('slug') != 'first-gen' else b.get('tag'), _span(b['videos'])) if x)
    return ('<a class="yt-card yt-bundle" href="%s/videos/%s/">'
            '<span class="yt-stack">%s<span class="yt-count">%d편 ▸</span></span>'
            '<span class="yt-kicker">시리즈</span><strong>%s</strong><time>%s</time></a>'
            % (e(base), e(b['slug']), _thumb(first['id']), len(b['videos']), e(b['name']), e(sub)))


def videos_page(live, page_intro, base=''):
    cfg = site_config()
    yt = cfg.get('youtube') or {}
    series_cfg = (cfg.get('youtube_more') or [{}])[0]
    bundles = _bundles(load_catalog(live), series_cfg)
    out = [page_intro('유튜브', '솜니움의 세미나·강좌·북클럽 영상입니다. 최근 올라온 순서이고, 시리즈는 카드 하나로 묶었습니다 — 누르면 그 시리즈 영상을 차례대로 봅니다. 새 영상은 매일 아침 저절로 들어옵니다.', base)]
    out.append('<p class="yt-links"><a class="button yt-button" href="%s" target="_blank" rel="noopener">솜니움 유튜브 채널 ↗</a> '
               '<a class="button yt-button ghost" href="%s" target="_blank" rel="noopener">1기 「한국기독학생운동사를 돌아보며」 채널 ↗</a></p>'
               % (e(yt.get('url', '')), e(series_cfg.get('url', ''))))
    years = []
    for b in bundles:
        y = (b['latest'][0] or '')[:4] or '그 전'
        if not years or years[-1][0] != y:
            years.append((y, []))
        years[-1][1].append(b)
    out.append('<nav class="vid-toc" aria-label="연도">%s</nav>' % ''.join('<a href="#y%s">%s</a>' % (e(y), e(y)) for y, _ in years))
    for y, bs in years:
        cards = ''.join(_card(b['single']) if 'single' in b else _series_card(b, base) for b in bs)
        out.append('<section class="vid-group" id="y%s"><h2>%s</h2><div class="yt-grid">%s</div></section>' % (e(y), e(y), cards))
    return '\n'.join(out)


def series_pages(live, page_intro, base=''):
    """시리즈마다 쪽 하나: [(경로, 제목, 본문, 설명)]"""
    cfg = site_config()
    series_cfg = (cfg.get('youtube_more') or [{}])[0]
    pages = []
    for b in _bundles(load_catalog(live), series_cfg):
        if 'single' in b:
            continue
        lead = ' · '.join(x for x in (b.get('tag', ''), b.get('desc', ''), '%d편' % len(b['videos']), _span(b['videos'])) if x)
        intro = page_intro(b['name'], lead, base).replace(
            '<span aria-hidden="true">›</span> <span>',
            '<span aria-hidden="true">›</span> <a href="%s/videos/">유튜브</a> <span aria-hidden="true">›</span> <span>' % e(base), 1)
        body = [intro]
        body.append('<p class="yt-links"><a class="button yt-button ghost" href="%s/videos/">← 유튜브 전체 영상</a>%s</p>'
                    % (e(base), (' <a class="button yt-button" href="%s" target="_blank" rel="noopener">채널에서 보기 ↗</a>' % e(b['url'])) if b.get('url') else ''))
        items = ''.join('<li><span class="yt-ep">%d</span>%s</li>' % (i + 1, _card(v)) for i, v in enumerate(b['videos']))
        body.append('<ol class="yt-grid yt-episodes">%s</ol>' % items)
        pages.append(('videos/%s/index.html' % b['slug'], '유튜브 · ' + b['name'].split(' · ')[0], '\n'.join(body), lead))
    return pages
