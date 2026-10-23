"""검색엔진·AI 검색(ChatGPT·Claude·Perplexity·Gemini 등)이 솜니움을 정확히 읽도록 돕는 장치.
- 쪽마다: 설명(meta description), 공유 미리보기(Open Graph), 대표 주소(canonical)
- 구조화 정보(JSON-LD): 단체 정보 + 날짜가 정해진 모임(Event)
- 사이트 전체: robots.txt(AI 수집기 허용), sitemap.xml, llms.txt(AI용 요약)
값은 config/site.json 과 시트에서만 옵니다. 지어낸 정보는 넣지 않습니다."""
import json
from html import escape as e

from data import public_rows
from extras import site_config

AI_BOTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
           'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'CCBot']


def _site():
    c = site_config()
    return c, (c.get('site_url') or '').rstrip('/'), c.get('seo') or {}


def abs_url(rel, base=''):
    _, url, _ = _site()
    path = '/' + rel.replace('index.html', '').lstrip('/')
    return (url + path) if url else (base + path)


def org_jsonld():
    c, url, s = _site()
    same = [x.get('url') for x in [c.get('youtube') or {}] + list(c.get('youtube_more') or []) + [c.get('instagram') or {}, c.get('facebook') or {}] if x.get('url')]
    org = {'@context': 'https://schema.org', '@type': ['Organization', 'EducationalOrganization'],
           'name': s.get('name', '솜니움 기독교정치사회연구소'), 'alternateName': s.get('alternate_names', []),
           'description': s.get('description', ''), 'email': c.get('email', ''), 'sameAs': same,
           'foundingDate': s.get('founding_date', ''), 'keywords': ', '.join(s.get('keywords', []))}
    if s.get('address'):
        org['address'] = dict({'@type': 'PostalAddress'}, **s['address'])
    if url:
        org['url'] = url + '/'
        org['logo'] = url + '/assets/og-default.png'
    return {k: v for k, v in org.items() if v}


def _place(text):
    """「솜니움 모임공간(합정) · 줌」 → 장소 + 온라인. 줌만 있으면 온라인만."""
    _, _, s = _site()
    text = (text or '').strip()
    if not text:
        return []
    online = '줌' in text or '온라인' in text
    name = text
    for w in ('+ 온라인 줌', '온라인 줌', '· 줌', '+ 줌', '줌', '온라인'):
        name = name.replace(w, '')
    name = name.strip(' ·+,')
    places = []
    if name:
        places.append({'@type': 'Place', 'name': name, 'address': dict({'@type': 'PostalAddress'}, **(s.get('address') or {}))})
    if online:
        places.append({'@type': 'VirtualLocation', 'name': '줌(Zoom) 온라인'})
    return places


def events_jsonld(tables, base=''):
    c, url, s = _site()
    org = {'@type': 'Organization', 'name': s.get('name', '솜니움 기독교정치사회연구소')}
    if url:
        org['url'] = url + '/'
    seminars = {x.get('id'): x for x in public_rows(tables, '세미나')}
    fac = {f['id']: f for f in public_rows(tables, '강사진')}
    out = []

    def make(name, date, time, sem, href, desc):
        start = date + ('T%s:00+09:00' % time if time else '')
        ev = {'@context': 'https://schema.org', '@type': 'Event', 'name': name, 'startDate': start,
              'eventStatus': 'https://schema.org/EventScheduled', 'organizer': org, 'url': abs_url(href.lstrip('/'), '')}
        if desc:
            ev['description'] = desc[:300]
        place = (sem or {}).get('장소', '')
        locs = _place(place)
        if locs:
            ev['location'] = locs if len(locs) > 1 else locs[0]
            ev['eventAttendanceMode'] = ('https://schema.org/MixedEventAttendanceMode' if len(locs) > 1 else
                                         'https://schema.org/OnlineEventAttendanceMode' if locs[0]['@type'] == 'VirtualLocation'
                                         else 'https://schema.org/OfflineEventAttendanceMode')
        perf = [fac[i.strip()]['이름'] for i in ((sem or {}).get('강사진_id') or '').split(';') if i.strip() in fac]
        if perf:
            ev['performer'] = [{'@type': 'Person', 'name': n} for n in perf]
        if (sem or {}).get('신청_url'):
            ev['offers'] = {'@type': 'Offer', 'url': sem['신청_url'], 'availability': 'https://schema.org/InStock'}
        return ev

    for r in public_rows(tables, '회차'):
        sem = seminars.get(r.get('세미나_id'))
        if not sem or not r.get('날짜') or sem.get('상태') == '취소':
            continue
        out.append(make('%s %s회 · %s' % (sem.get('제목', ''), r.get('회차', ''), r.get('제목', '')), r['날짜'], r.get('시간', ''),
                        sem, 'seminars/%s/' % sem.get('id'), sem.get('소개', '')))
    for b in public_rows(tables, '북클럽'):
        if b.get('날짜') and b.get('상태') != '취소':
            out.append(make('솜니움 %s 『%s』' % (b.get('제목', ''), b.get('도서', '')), b['날짜'], b.get('시간', ''),
                            {'장소': b.get('장소', ''), '신청_url': b.get('신청_url', '')}, 'programs/', b.get('소개', '')))
    return out


def head_tags(rel, title, description, base='', image=None, jsonld=None):
    c, url, s = _site()
    desc = (description or s.get('description', '')).replace('\n', ' ').strip()[:160]
    page_url = abs_url(rel)
    img = image or ((url + '/assets/og-default.png') if url else (base + '/assets/og-default.png'))
    tags = ['<meta name="description" content="%s">' % e(desc),
            '<meta name="keywords" content="%s">' % e(', '.join(s.get('keywords', []))),
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="%s">' % e(s.get('name', '')),
            '<meta property="og:locale" content="ko_KR">',
            '<meta property="og:title" content="%s">' % e(title),
            '<meta property="og:description" content="%s">' % e(desc),
            '<meta property="og:image" content="%s">' % e(img),
            '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
            '<meta name="twitter:card" content="summary_large_image">']
    ver = c.get('verification') or {}
    if ver.get('google'):
        tags.append('<meta name="google-site-verification" content="%s">' % e(ver['google']))
    if ver.get('naver'):
        tags.append('<meta name="naver-site-verification" content="%s">' % e(ver['naver']))
    if url:
        tags.append('<link rel="canonical" href="%s">' % e(page_url))
        tags.append('<meta property="og:url" content="%s">' % e(page_url))
    for block in jsonld or []:
        tags.append('<script type="application/ld+json">%s</script>'
                    % json.dumps(block, ensure_ascii=False).replace('</', '<\\/'))
    return '\n'.join(tags)


def robots_txt():
    _, url, _ = _site()
    lines = ['# 솜니움: 검색엔진과 AI 검색 모두 환영합니다.', 'User-agent: *', 'Allow: /', '']
    for bot in AI_BOTS:
        lines += ['User-agent: %s' % bot, 'Allow: /', '']
    if url:
        lines.append('Sitemap: %s/sitemap.xml' % url)
    return '\n'.join(lines) + '\n'


def sitemap_xml(rels):
    _, url, _ = _site()
    if not url:
        return None
    items = ''.join('<url><loc>%s</loc></url>' % e(abs_url(r)) for r in rels)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % items


def llms_txt(tables, base=''):
    """AI가 사이트를 한 번에 이해하도록 쓰는 요약 (llmstxt.org 형식)."""
    c, url, s = _site()
    L = ['# %s' % s.get('name', '솜니움 기독교정치사회연구소'), '',
         '> %s' % s.get('description', ''), '',
         '- 다른 이름: %s' % ', '.join(s.get('alternate_names', [])),
         '- 활동 시작: %s' % s.get('founding_date', ''),
         '- 주소: 서울 %s %s' % ((s.get('address') or {}).get('addressLocality', ''), (s.get('address') or {}).get('streetAddress', '')),
         '- 이메일: %s' % c.get('email', ''), '']
    L += ['## 지금 하는 공부', '']
    for x in public_rows(tables, '세미나'):
        when = ' – '.join(v for v in (x.get('시작일', ''), x.get('종료일', '')) if v)
        L.append('- [%s](%s): %s%s%s' % (x.get('제목', ''), abs_url('seminars/%s/' % x.get('id'), base),
                 x.get('상태', ''), (' · ' + when) if when else '', (' · ' + x.get('부제', '')) if x.get('부제') else ''))
    books = public_rows(tables, '북클럽')
    if books:
        L += ['', '## 북클럽', '']
        L += ['- %s 『%s』 (%s)' % (b.get('제목', ''), b.get('도서', ''), b.get('상태', '')) for b in books]
    L += ['', '## 참여·후원', '',
          '- 참가 신청과 후원 계좌: %s' % abs_url('participate/', base)]
    L += ['', '## 채널', '']
    for x in [c.get('youtube') or {}] + list(c.get('youtube_more') or []) + [c.get('instagram') or {}, c.get('facebook') or {}]:
        if x.get('url'):
            L.append('- %s: %s' % (x.get('이름', ''), x['url']))
    L += ['', '## 쪽', '',
          '- [연구소 소개](%s): 정신·미션·이사회·연혁·오시는 길' % abs_url('about/', base),
          '- [프로그램](%s): 세미나·북클럽·기획강좌' % abs_url('programs/', base),
          '- [지난 프로그램](%s): 2017년 창립 이후 세미나·강좌 목록' % abs_url('archive/', base)]
    return '\n'.join(L) + '\n'
