import html
from html import escape as e
from data import public_rows
from extras import month_calendar, youtube_section, social_strip, footer_social, accounts_block


def _asset_version():
    """CSS·JS 내용이 바뀌면 주소 꼬리(?v=)가 바뀌어, 브라우저가 옛 디자인을 붙들고 있지 않게 한다."""
    import hashlib
    from pathlib import Path
    h = hashlib.md5()
    for f in sorted((Path(__file__).resolve().parent.parent / 'assets').glob('*.[cj]s*')):
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


ASSET_VER = _asset_version()


def _page_steps(title, base, nav):
    """홈이 아닌 쪽 아래에 «이전 메뉴 · 홈 · 다음 메뉴»와 «뒤로» 단추."""
    if title == '홈':
        return ''
    pages = [(l, h) for l, h in nav if not h.startswith('/#')]
    labels = [l for l, _ in pages]
    if title in labels:
        i = labels.index(title)
        prev = pages[i - 1] if i > 0 else None
        nxt = pages[i + 1] if i + 1 < len(pages) else None
    elif title.startswith('유튜브 · '):
        prev, nxt = ('유튜브', '/videos/'), None
    else:
        prev, nxt = ('프로그램', '/programs/'), None
    left = f'<a class="step-prev" href="{base}{prev[1]}">← {e(prev[0])}</a>' if prev else '<span></span>'
    right = f'<a class="step-next" href="{base}{nxt[1]}">{e(nxt[0])} →</a>' if nxt else '<span></span>'
    return (f'<nav class="page-steps" aria-label="쪽 이동">{left}'
            f'<span class="step-mid"><button type="button" class="step-back" onclick="history.length>1?history.back():location.href=\'{base}/\'">뒤로</button>'
            f'<a class="step-home" href="{base}/">홈으로</a></span>{right}</nav>')


def shell(title, body, base='', theme='b', preview=False):
    t = e(title)
    nav = [('이달의 프로그램', '/#cal'), ('프로그램', '/programs/'), ('유튜브', '/videos/'), ('지난 프로그램', '/archive/'), ('연구소 소개', '/about/'), ('참여·후원', '/participate/')]
    navhtml = ''.join(f'<a href="{base}{h}"' + (' aria-current="page"' if title == l else '') + f'>{e(l)}</a>' for l, h in nav)
    banner = '<div class="preview-banner">검토용 / 프로그램 일정과 신청 안내를 확인하고 있습니다</div>' if preview else ''
    return f'''<!DOCTYPE html>
<html lang="ko" class="theme-{e(theme)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>window.somniumDefaultTheme="{e(theme)}";</script>
<script src="{base}/assets/theme.js?v={ASSET_VER}"></script>
<title>{('솜니움 기독교정치사회연구소 — 연구자와 시민이 만나는 광장' if title == '홈' else t + ' | 솜니움 기독교정치사회연구소')}</title>
<link rel="preload" href="{base}/assets/SomniumDisplay.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{base}/assets/site.css?v={ASSET_VER}">
<link rel="stylesheet" href="{base}/assets/pages.css?v={ASSET_VER}">
<link rel="stylesheet" href="{base}/assets/extras.css?v={ASSET_VER}">
<link rel="stylesheet" href="{base}/assets/tokens.css?v={ASSET_VER}">
<link rel="stylesheet" href="{base}/assets/fonts-display.css?v={ASSET_VER}">
<link rel="stylesheet" href="{base}/assets/plaza.css?v={ASSET_VER}">
<script src="{base}/assets/extras.js?v={ASSET_VER}" defer></script>
<link rel="icon" href="{base}/assets/favicon.png">
</head>
<body>
{banner}
<a class="skip-link" href="#main">본문으로 건너뛰기</a>
<header class="site-header">
<div class="header-inner">
<a class="logo" href="{base}/"><strong>somnium</strong><span>솜니움 기독교정치사회연구소</span></a>
<div class="header-actions"><nav class="site-nav" aria-label="주요 메뉴">{navhtml}</nav>
<div class="theme-switch hidden" data-theme-switch role="group" aria-label="화면 밝기"><button type="button" data-theme-choice="a" aria-pressed="false">어둡게</button><button type="button" data-theme-choice="b" aria-pressed="false">밝게</button></div></div>
</div>
</header>
<main class="container" id="main">
{body}
{_page_steps(title, base, nav)}
</main>
<footer class="site-footer">
<div class="container">
<h2>함께 배우고,<br>토론하며, 꿈을 꿉니다.</h2>
<div class="footer-links">
<a href="{base}/about/">연구소 소개</a>
<a href="{base}/programs/">프로그램</a>
<a href="{base}/participate/">참여·후원</a>
<a href="mailto:agit.somnium@gmail.com">agit.somnium@gmail.com</a>
{footer_social()}
</div>
<p class="footer-family">함께하는 곳 · <a href="https://gilseop.com/" target="_blank" rel="noopener">길섶교회</a> · <a href="https://yesuchurch.com/" target="_blank" rel="noopener">한국예수교회연대</a> · <a href="https://faithseeking.net/" target="_blank" rel="noopener">신학브리핑 웹진</a></p>
</div>
</footer>
</body>
</html>'''


def _status(s):
    return e((s or '').strip() or '일정 확인 중')


def home(tables, base='', videos=None):
    out = []
    out.append('<section class="hero">')
    out.append('<div class="hero-copy"><p class="hero-label">연구자와 시민이 만나는 광장</p>')
    out.append('<h1>우리가 살아갈<br><span>사회를 연구합니다.</span></h1></div>')
    out.append('<div class="hero-intro"><p>정치사회이론을 함께 읽고, 시민의 경험을 나눕니다. 기독교와 사회가 만나는 자리에서 다음 질문을 찾습니다.</p>')
    out.append(f'<a class="plain-link" href="{base}/about/">솜니움 알아보기 ↗</a></div>')
    out.append('</section>')
    out.append(month_calendar(tables, base))

    qs = [
        ('자본주의는 우리의 일과 삶을 어떻게 바꾸고 있을까요?', '노동과 삶을 둘러싼 정치경제의 변화를 함께 읽습니다.'),
        ('기독교는 어떤 시민의 삶을 만들 수 있을까요?', '기독교의 전통을 정치사회 현실과 함께 살펴봅니다.'),
        ('이론이 놓치는 주변부의 경험은 무엇일까요?', '기존의 설명에 담기지 않은 삶의 목소리를 따라갑니다.'),
        ('함께 공부하는 일은 어떤 변화를 만들 수 있을까요?', '연구자의 언어와 시민의 경험을 나누고, 다음 공부로 이어갑니다.'),
    ]
    out.append('<section class="research" aria-labelledby="research-title">')
    out.append('<div class="section-heading"><h2 id="research-title">지금, 우리가 묻는 것</h2><p>함께 읽고 토론하며 답을 찾아갑니다.</p></div>')
    out.append('<div class="research-grid">')
    for q, d in qs:
        out.append(f'<details class="research-question"><summary>{e(q)}<span aria-hidden="true">+</span></summary><p>{e(d)}</p></details>')
    out.append('</div></section>')

    out.append('<div class="method-line"><p>읽기 → 질문하기 → 토론하기 → 기록하기</p><span>읽은 것을 질문으로, 질문을 토론으로, 토론을 기록으로 남깁니다.</span></div>')

    out.append('<section class="programs"><h2>함께하는 공부</h2>')
    seminars = public_rows(tables, '세미나')
    if seminars:
        first = seminars[0]
        out.append('<article class="seminar-feature"><div class="feature-copy">')
        st = _home_status(first)
        if st:
            out.append(f'<p class="feature-status">{st}</p>')
        out.append(f'<h3>{e(first.get("제목", ""))}</h3>')
        if first.get('부제'):
            out.append(f'<p class="feature-subtitle">{e(first["부제"])}</p>')
        if first.get('소개'):
            out.append(f'<p class="feature-intro">{e(first["소개"])}</p>')
        out.append(f'<a class="feature-link" href="{base}/seminars/{e(first.get("id", ""))}/">세미나 내용과 일정 보기 ↗</a>')
        out.append('</div>')
        meta = []
        if first.get('강사진_id'):
            names = [f['이름'] for f in public_rows(tables, '강사진') if f['id'] in first['강사진_id'].split(';')]
            meta.append('<span>강사진</span><strong>' + e(' · '.join(names)) + '</strong>')
        if first.get('시작일'):
            meta.append(f'<span>{e(first["시작일"])}</span>')
        if meta:
            out.append('<div class="feature-meta">' + ''.join(meta) + '</div>')
        out.append('</article>')
        rest = seminars[1:]
        if rest:
            out.append('<div class="seminar-index"><h3>다음 공부와 지난 기록</h3><ul>')
            for s in rest:
                st = _home_status(s)
                stt = f' <em>{st}</em>' if st else ''
                out.append(f'<li><a href="{base}/seminars/{e(s.get("id", ""))}/">{e(s.get("제목", ""))}</a>{stt}</li>')
            out.append('</ul></div>')
    else:
        out.append('<p class="empty">진행 중인 세미나 일정을 준비하고 있습니다.</p>')
    out.append('</section>')

    books = public_rows(tables, '북클럽')
    posters = {'book-october': 'sonjeol.webp', 'book-november': 'gakkaseuro.webp'}
    out.append('<section class="bookclub"><h2>책에서 시작하는 대화</h2>')
    if books:
        out.append('<div class="bookclub-grid">')
        for b in books:
            bid = b.get('id', '')
            out.append('<article class="book-card">')
            if bid in posters:
                out.append(f'<a href="{base}/programs/#book-{e(bid)}"><img src="{base}/assets/{posters[bid]}" alt="{e(b.get("도서", ""))} 도서" width="864" height="1080" loading="lazy"></a>')
            out.append(f'<h3>{e(b.get("도서", ""))}</h3>')
            if b.get('제목'):
                out.append(f'<p class="book-title">{e(b["제목"])}</p>')
            st = _home_status(b)
            if st:
                out.append(f'<p class="book-status">{st}</p>')
            out.append('</article>')
        out.append('</div>')
    else:
        out.append('<p class="empty">북클럽 도서를 준비하고 있습니다.</p>')
    out.append('</section>')

    out.append(youtube_section(videos or []))
    out.append(f'<p class="archive-more"><a class="plain-link" href="{base}/archive/">2017년부터 걸어온 프로그램 보기 →</a></p>')

    notices = public_rows(tables, '공지')
    if notices:
        out.append('<section class="notice-strip"><h2>소식</h2>')
        for n in notices:
            out.append('<article>')
            out.append(f'<h3>{e(n.get("제목", ""))}</h3>')
            if n.get('본문'):
                out.append(f'<p>{e(n["본문"])}</p>')
            if n.get('링크_url'):
                out.append(f'<a href="{e(n["링크_url"])}">소식 확인하기 ↗</a>')
            out.append('</article>')
        out.append('</section>')

    out.append(social_strip())
    out.append(accounts_block(compact=True))
    return '\n'.join(out)


def seminar_detail(s, tables, base=''):
    sid = str(s.get('id', ''))
    status = (s.get('상태') or '').strip()
    sessions = [x for x in public_rows(tables, '회차') if str(x.get('세미나_id', '')) == sid]
    sessions.sort(key=lambda x: int(x.get('회차') or 0))
    faculty = public_rows(tables, '강사진')
    fids = [f.strip() for f in (s.get('강사진_id') or '').split(';') if f.strip()]
    vids = public_rows(tables, '영상')
    by_round = {}
    for v in vids:
        if str(v.get('세미나_id', '')) == sid:
            by_round.setdefault(str(v.get('회차_id', '')), []).append(v)
    used = set()
    out = ['<div class="detail-layout"><article class="prose">']
    out.append('<h1>' + e(s.get('제목', '')) + '</h1>')
    if s.get('부제'):
        out.append('<p class="subtitle">' + e(s.get('부제')) + '</p>')
    out.append('<p class="status">' + _status(status) + '</p>')
    for para in (s.get('소개') or '').split('\n'):
        if para.strip():
            out.append('<p>' + e(para.strip()) + '</p>')
    out.append('<h2>' + e('함께 공부할 내용') + '</h2>')
    if sessions:
        out.append('<ol class="sessions">')
        for x in sessions:
            xid = str(x.get('id', ''))
            when = (x.get('날짜') or '').strip()
            tm = (x.get('시간') or '').strip()
            when = (when + ' ' + tm).strip() or '일정 확인 중'
            out.append('<li id="session-' + e(xid) + '">')
            out.append('<strong>' + e(str(x.get('회차', ''))) + '회차</strong> ' + e(x.get('제목', '')) + ' · ' + e(when))
            mat = (x.get('자료_url') or '').strip()
            if mat:
                out.append(' <a href="' + e(mat) + '">' + e('자료') + '</a>')
            for v in by_round.get(xid, []):
                used.add(id(v))
                url = (v.get('youtube_url') or '').strip()
                label = e(v.get('제목', '')) + ' ' + e('영상')
                if url:
                    out.append(' <a class="video" href="' + e(url) + '">' + label + '</a>')
                else:
                    out.append(' <span class="video">' + label + '</span>')
            out.append('</li>')
        out.append('</ol>')
    else:
        out.append('<p class="empty">' + e('아직 공개된 회차가 없습니다.') + '</p>')
    out.append('<h2>' + e('지난 자료') + '</h2>')
    rest = [v for v in vids if str(v.get('세미나_id', '')) == sid and id(v) not in used]
    if rest:
        out.append('<ul>')
        for v in rest:
            url = (v.get('youtube_url') or '').strip()
            if url:
                out.append('<li><a href="' + e(url) + '">' + e(v.get('제목', '')) + '</a></li>')
            else:
                out.append('<li>' + e(v.get('제목', '')) + '</li>')
        out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('등록된 지난 자료가 없습니다.') + '</p>')
    out.append('<h2>' + e('강사진') + '</h2>')
    matched = [f for f in faculty if str(f.get('id', '')) in fids]
    if matched:
        out.append('<ul class="faculty-list">')
        for f in matched:
            out.append('<li>')
            img = (f.get('사진_url') or '').strip()
            if img:
                out.append('<img src="' + e(img) + '" alt="' + e(f.get('이름', '')) + '" width="120" height="120" loading="lazy">')
            out.append('<strong>' + e(f.get('이름', '')) + '</strong> ' + e(f.get('소개', '')) + '</li>')
        out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('강사진 정보를 준비하고 있습니다.') + '</p>')
    out.append('</article><aside class="summary"><h2>' + e('참여 안내') + '</h2>')
    out.append('<p>' + e('시작') + ': ' + e((s.get('시작일') or '').strip() or '일정 확인 중') + '</p>')
    out.append('<p>' + e('종료') + ': ' + e((s.get('종료일') or '').strip() or '일정 확인 중') + '</p>')
    out.append('<p>' + e('장소') + ': ' + e((s.get('장소') or '').strip() or '장소 확인 중') + '</p>')
    url = (s.get('신청_url') or '').strip()
    if status == '취소':
        out.append('<p class="cancelled"><strong>' + e('취소') + '</strong> ' + e((s.get('취소사유') or '').strip() or '사유 확인 중') + '</p>')
    elif status == '종료':
        out.append('<p>' + e('종료된 세미나입니다. 지난 자료를 계속 볼 수 있습니다.') + '</p>')
    elif status in ('모집중', '진행중') and url:
        out.append('<p><a class="button" href="' + e(url) + '">' + e('신청하기') + '</a></p>')
    else:
        out.append('<p>' + e('신청 안내를 준비하고 있습니다.') + '</p>')
    out.append('<nav aria-label="' + e('프로그램 이동') + '"><a href="' + e(base + '/programs/') + '">' + e('전체 프로그램') + '</a></nav>')
    out.append('</aside></div>')
    return '\n'.join(out)

def _home_status(row):
    s = row.get('상태', '')
    return e(s) if s else ''
