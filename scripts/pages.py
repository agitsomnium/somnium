import re
from extras import accounts_block, board_frame, fmt_days
from data import public_rows
from html import escape as e

_SAFE_BASE = re.compile(r'^(/[\w\-./]*)?$')

def _base(b):
    b = b or ''
    if not _SAFE_BASE.match(b):
        return ''
    return b.rstrip('/')

def clean_content(text):
    if not text:
        return ''
    lines = text.splitlines()
    out = []
    skipped_title = False
    for ln in lines:
        if not skipped_title and re.match(r'^#\s+', ln):
            skipped_title = True
            continue
        out.append(ln)
    # strip trailing paragraphs starting with 출처: and the preservation note
    while out and not out[-1].strip():
        out.pop()
    while out:
        last = out[-1].strip()
        if last.startswith('출처:') or last.startswith('2026-10-18 원문 보존'):
            out.pop()
            while out and not out[-1].strip():
                out.pop()
            continue
        break
    return '\n'.join(out).strip()

def page_intro(title, lead, base=''):
    b = _base(base)
    return (
        '<header class="page-intro">'
        f'<nav class="breadcrumb" aria-label="위치"><a href="{e(b + "/")}">홈</a> <span aria-hidden="true">›</span> <span>{e(title)}</span></nav>'
        f'<h1>{e(title)}</h1>'
        f'<p>{e(lead)}</p>'
        '</header>'
    )

def _sources(md_texts):
    links = []
    seen = set()
    for t in md_texts:
        for m in re.finditer(r'\[([^\]]+)\]\((https?://somnium\.oopy\.io[^\s)]*)\)', t or ''):
            label, url = m.group(1), m.group(2)
            if url in seen:
                continue
            seen.add(url)
            links.append(f'<li><a href="{e(url)}">{e(label)}</a></li>')
    return links

def about_page(content, md, base=''):
    import html as _html
    b = _html.escape(base, quote=True)
    spirit = clean_content(content.get('about.md', ''))
    board = clean_content(content.get('board.md', ''))
    history = clean_content(content.get('history.md', ''))
    visit = clean_content(content.get('visit.md', ''))
    raw = [content.get('about.md', ''), content.get('board.md', ''), content.get('history.md', ''), content.get('visit.md', '')]
    sources = _sources(raw)
    toc = [('spirit', '솜니움의 정신'), ('board', '이사회'), ('history', '걸어온 길'), ('people', '함께한 사람들'), ('visit', '오시는 길')]
    people = clean_content(content.get('people.md', ''))
    toc_html = ''.join('<li><a href="#%s">%s</a></li>' % (i, t) for i, t in toc)
    src_html = ''.join(sources)
    return (
        page_intro('연구소 소개', '연구자와 시민이 만나, 기독교와 정치사회 현실을 함께 공부합니다.', base)
        + '<nav class="page-toc" aria-label="목차"><ul>' + toc_html + '</ul></nav>'
        + '<div class="reading-layout">'
        + '<aside class="reading-note">'
        + '<p class="reading-note-motto">기독교와 정치사회 현실을 함께 공부합니다.</p>'
        + '<p><a href="mailto:agit.somnium@gmail.com">agit.somnium@gmail.com</a></p>'
        + '</aside>'
        + '<article class="reading-body">'
        + '<section id="spirit"><h2>솜니움의 정신</h2>' + md(spirit) + '</section>'
        + '<section id="board"><h2>이사회</h2>' + board_frame() + '</section>'
        + '<section id="history"><h2>걸어온 길</h2>' + md(history)
        + '<p><a class="text-link" href="' + b + '/archive/">해마다 정리한 지난 프로그램 보기 →</a></p></section>'
        + '<section id="people"><h2>함께한 사람들</h2>' + md(people) + '</section>'
        + '<section id="visit"><h2>오시는 길</h2>' + md(visit)
        + '<figure><img src="' + b + '/assets/visit-building.webp" width="1196" height="900" loading="lazy" alt="솜니움 사무실이 있는 건물"></figure>'
        + '<p><a href="https://map.naver.com/p/search/%EC%84%9C%EC%9A%B8%20%EB%A7%88%ED%8F%AC%EA%B5%AC%20%EB%8F%85%EB%A7%89%EB%A1%9C%2043" target="_blank" rel="noopener">네이버지도에서 길찾기↗</a></p>'
        + '</section>'
        + '</article>'
        + '</div>'
        + '<footer class="source-footer"><details class="source-note"><summary>자료출처</summary>'
        + '<p>이사회·주소 등 운영 정보는 기존 공개 자료를 옮겼습니다.</p>'
        + '<ul>' + src_html + '</ul></details></footer>'
    )



def program_page(tables, content, md, base=''):
    base = base or ''
    if base and not base.startswith('/'):
        base = '/' + base
    base = base.rstrip('/')

    def g(r, k, d=''):
        v = r.get(k, d)
        return '' if v is None else str(v)

    def status(r):
        return g(r, '상태').strip()

    sems = public_rows(tables, '세미나')
    books = public_rows(tables, '북클럽')

    inst = {}
    for r in public_rows(tables, '강사진'):
        inst[g(r, 'id').strip()] = g(r, '이름').strip() or g(r, '제목').strip()

    def names(raw):
        out = []
        for part in (raw or '').split(';'):
            pid = part.strip()
            if pid and pid in inst and inst[pid]:
                out.append(inst[pid])
        return ', '.join(out)

    def dates(r):
        s, en = g(r, '시작일').strip(), g(r, '종료일').strip()
        if s and en and s != en:
            return e(s) + ' ~ ' + e(en)
        if s:
            return e(s)
        if en:
            return e(en)
        return '일정 확인 중'

    def tile(r, featured=False):
        sid = g(r, 'id').strip()
        st = status(r)
        cls = 'program-tile' + (' featured' if featured else '')
        h = ['<article class="%s">' % cls]
        h.append('<div class="tile-top">%s</div>' % e(st))
        h.append('<h3><a href="%s/seminars/%s/">%s</a></h3>' % (e(base), e(sid), e(g(r, '제목'))))
        sub = g(r, '부제').strip()
        if sub:
            h.append('<p class="tile-subtitle">%s</p>' % e(sub))
        intro = g(r, '소개').strip()
        if intro:
            h.append('<p class="tile-intro">%s</p>' % e(intro))
        h.append('<p class="tile-dates">%s</p>' % dates(r))
        nm = names(g(r, '강사진_id'))
        if nm:
            h.append('<p class="tile-instructors">%s</p>' % e(nm))
        if st == '취소':
            reason = g(r, '취소사유').strip()
            if reason:
                h.append('<p class="tile-cancel">%s</p>' % e(reason))
        h.append('<a class="text-link" href="%s/seminars/%s/">세미나 내용과 일정 ↗</a>' % (e(base), e(sid)))
        h.append('</article>')
        return ''.join(h)

    active = [r for r in sems if status(r) != '종료']
    ended = [r for r in sems if status(r) == '종료']

    out = []
    out.append(page_intro('프로그램', '함께 읽고, 질문하고, 토론하는 공부에 초대합니다.', base))
    out.append('<nav class="page-toc" aria-label="프로그램 분류"><a href="#seminars">세미나</a> <a href="#bookclubs">북클럽</a> <a href="#lectures">기획강좌·특강</a> <a href="#agit">아지트솜니움</a></nav>')

    out.append('<section class="content-section" id="seminars">')
    out.append('<div class="section-head"><h2>세미나</h2><p>주제와 강사진, 회차별 자료를 한곳에서 만납니다.</p></div>')
    out.append('<div class="program-listing">')
    if active:
        for i, r in enumerate(active):
            out.append(tile(r, featured=(i == 0)))
    else:
        out.append('<p class="empty">현재 공개된 세미나가 없습니다.</p>')
    out.append('</div>')
    if ended:
        out.append('<details class="archive-fold"><summary>지난 세미나</summary><ul class="archive-list">')
        for r in ended:
            sid = g(r, 'id').strip()
            out.append('<li><a href="%s/seminars/%s/">%s</a> <span class="archive-state">%s</span></li>' % (e(base), e(sid), e(g(r, '제목')), e(status(r))))
        out.append('</ul></details>')
    out.append('</section>')

    imgs = {'book-october': ('assets/sonjeol.webp',), 'book-november': ('assets/gakkaseuro.webp',)}
    out.append('<section class="content-section" id="bookclubs">')
    out.append('<div class="section-head"><h2>북클럽</h2></div>')
    out.append('<div class="book-listing">')
    if books:
        for r in books:
            bid = g(r, 'id').strip()
            st = status(r)
            out.append('<article class="book-program" id="book-%s">' % e(bid))
            if bid in imgs:
                out.append('<aside class="book-cover"><img src="%s/%s" width="864" height="1080" loading="lazy" alt="%s 북클럽 안내"></aside>' % (e(base), e(imgs[bid][0]), e(g(r, '도서') or g(r, '제목'))))
            out.append('<div class="book-copy">')
            out.append('<p class="book-state">%s</p>' % e(st))
            title = g(r, '도서').strip() or g(r, '제목').strip()
            out.append('<h3>%s</h3>' % e(title))
            desc = g(r, '소개').strip()
            if desc:
                out.append('<p>%s</p>' % e(desc))
            out.append('<dl class="detail-facts">')
            d = g(r, '날짜').strip()
            t = g(r, '시간').strip()
            loc = g(r, '장소').strip()
            if d:
                out.append('<dt>날짜</dt><dd>%s</dd>' % e(fmt_days(d)))
            if t:
                out.append('<dt>시간</dt><dd>%s</dd>' % e(t))
            if loc:
                out.append('<dt>장소</dt><dd>%s</dd>' % e(loc))
            if not (d or t or loc):
                out.append('<dt>일정</dt><dd>일정 미정</dd>')
            out.append('</dl>')
            if st == '취소':
                reason = g(r, '취소사유').strip()
                if reason:
                    out.append('<p class="book-cancel">%s</p>' % e(reason))
            elif st in ('모집중', '진행중'):
                url = g(r, '신청_url').strip()
                if url:
                    out.append('<a class="button" href="%s">신청하기 ↗</a>' % e(url))
                else:
                    out.append('<a class="text-link" href="mailto:agit.somnium@gmail.com">참여 문의 ↗</a>')
            elif st == '종료':
                out.append('<p class="book-archived">종료된 프로그램입니다.</p>')
            else:
                out.append('<a class="text-link" href="mailto:agit.somnium@gmail.com">참여 문의 ↗</a>')
            out.append('</div></article>')
    else:
        out.append('<p class="empty">현재 공개된 북클럽이 없습니다.</p>')
    out.append('</div></section>')

    out.append('<section class="content-section" id="lectures"><div class="split-content">')
    out.append('<div class="split-main"><h2>기획강좌·특강</h2>')
    out.append(md(clean_content(content.get('lectures.md', ''))))
    out.append('<a class="text-link" href="%s/archive/">2017년부터 걸어온 프로그램 보기 →</a>' % e(base))
    out.append('</div></div></section>')

    out.append('<section class="content-section" id="agit"><h2>아지트솜니움</h2>')
    out.append(md(clean_content(content.get('agit.md', ''))))
    out.append('<a class="button" href="mailto:agit.somnium@gmail.com">문의하기</a>')
    out.append('</section>')

    return ''.join(out)

def resources_page(tables, base=''):
    out = [page_intro('연구자료', '함께 공부한 시간을 영상과 자료로 다시 만납니다.', base)]
    out.append('<section class="content-section"><h2>영상 아카이브</h2>')
    out.append('<div class="channel-grid">')
    out.append('<a class="channel-card" href="https://www.youtube.com/@솜니움정치사회연구소" target="_blank" rel="noopener">'
               '<span class="channel-name">솜니움정치사회연구소</span>'
               '<small>유튜브 채널로 이동 ↗</small></a>')
    out.append('<a class="channel-card" href="https://www.youtube.com/@솜니움Somnium" target="_blank" rel="noopener">'
               '<span class="channel-name">솜니움Somnium</span>'
               '<small>유튜브 채널로 이동 ↗</small></a>')
    out.append('</div>')
    sems = public_rows(tables, '세미나') or []
    sem_ids = set()
    for s in sems:
        sid = s.get('id')
        if sid not in (None, ''):
            sem_ids.add(str(sid))
    videos = public_rows(tables, '영상') or []
    items = []
    for v in videos:
        title = v.get('제목')
        url = v.get('youtube_url')
        if not title or not url:
            continue
        li = f'<li><a href="{e(str(url))}" target="_blank" rel="noopener">{e(str(title))}</a>'
        date = v.get('날짜')
        if date not in (None, ''):
            li += f' <span class="meta">{e(str(date))}</span>'
        sem = v.get('세미나_id')
        if sem not in (None, '') and str(sem) in sem_ids:
            li += f' <a class="sem-link" href="{e(base)}/seminars/{e(str(sem))}/">관련 세미나</a>'
        li += '</li>'
        items.append(li)
    if items:
        out.append('<ul class="resource-list">' + ''.join(items) + '</ul>')
    else:
        out.append('<p class="muted">회차별 영상 목록을 정리하고 있습니다. 공개 영상은 위 채널에서 보실 수 있습니다.</p>')
    out.append('</section>')
    out.append('<section class="content-section"><h2>세미나별 자료</h2>')
    sitems = []
    for s in sems:
        sid = s.get('id')
        title = s.get('제목')
        if sid in (None, '') or not title:
            continue
        li = f'<li><a href="{e(base)}/seminars/{e(str(sid))}/">{e(str(title))}</a>'
        state = s.get('상태')
        if state not in (None, ''):
            li += f' <span class="state">{e(str(state))}</span>'
        sub = s.get('부제')
        if sub not in (None, ''):
            li += f'<p class="subtitle">{e(str(sub))}</p>'
        li += '</li>'
        sitems.append(li)
    if sitems:
        out.append('<ul class="resource-seminars">' + ''.join(sitems) + '</ul>')
    else:
        out.append('<p class="muted">세미나별 자료를 준비하고 있습니다.</p>')
    out.append('</section>')
    out.append('<section class="editorial-callout"><h2>강의 정리글</h2>'
               '<p>강의의 주요 내용과 토론의 질문을 글로 남깁니다. 정리글은 강사 확인을 거쳐 공개합니다.</p></section>')
    return '\n'.join(out)

def participate_page(tables, content, md, base=''):
    out = [page_intro('참여·후원', '함께 공부하는 자리와 연구소의 다음 활동을 이어 주세요.', base)]
    out.append('<nav class="page-toc"><a href="#join">프로그램 참여</a> '
               '<a href="#support">후원·계좌</a> <a href="#contact">문의</a></nav>')
    out.append('<section id="join" class="content-section"><h2>프로그램에 참여하기</h2>')
    out.append('<p>세미나와 북클럽의 내용과 일정을 살펴보고 참여하실 수 있습니다.</p>')
    active = ('모집중', '진행중')
    items = []
    for s in public_rows(tables, '세미나') or []:
        state = s.get('상태')
        if state not in active:
            continue
        sid = s.get('id')
        title = s.get('제목')
        if sid in (None, '') or not title:
            continue
        url = s.get('신청_url')
        li = f'<li><a href="{e(base)}/seminars/{e(str(sid))}/">{e(str(title))}</a> <span class="state">{e(str(state))}</span>'
        if url not in (None, ''):
            li += f' <a class="button" href="{e(str(url))}" target="_blank" rel="noopener">신청하기</a>'
        else:
            li += ' <a class="text-link" href="mailto:agit.somnium@gmail.com">참여 문의</a>'
        li += '</li>'
        items.append(li)
    for b in public_rows(tables, '북클럽') or []:
        state = b.get('상태')
        if state not in active:
            continue
        bid = b.get('id')
        title = b.get('제목')
        if bid in (None, '') or not title:
            continue
        url = b.get('신청_url')
        li = f'<li><a href="{e(base)}/programs/#book-{e(str(bid))}">{e(str(title))}</a> <span class="state">{e(str(state))}</span>'
        if url not in (None, ''):
            li += f' <a class="button" href="{e(str(url))}" target="_blank" rel="noopener">신청하기</a>'
        else:
            li += ' <a class="text-link" href="mailto:agit.somnium@gmail.com">참여 문의</a>'
        li += '</li>'
        items.append(li)
    if items:
        out.append('<ul class="join-list">' + ''.join(items) + '</ul>')
    else:
        out.append('<p class="muted">현재 모집 중인 프로그램이 없습니다. 아래 전체 프로그램에서 지난 활동을 살펴보세요.</p>')
    out.append(f'<p><a class="text-link" href="{e(base)}/programs/">전체 프로그램 보기</a></p>')
    out.append('</section>')
    out.append('<section id="support" class="content-section"><h2>연구소를 후원하기</h2>')
    out.append('<p>솜니움은 한빛누리 공익기금 Bright Fund를 통해 정기후원을 받고 있습니다. 세미나 참가비도 아래 계좌로 보내 주시면 됩니다.</p>')
    out.append(accounts_block('후원·참가비 계좌'))
    out.append('<p class="source-note">기부금 영수증과 후원 절차는 한빛누리 안내를 확인해 주세요. '
               '<a href="https://somnium.oopy.io/184f8918-f72b-8049-8712-efdbe356f5c2" target="_blank" rel="noopener">후원 안내 원문</a></p>')
    out.append('</section>')
    out.append('<section id="contact" class="content-section"><h2>문의하기</h2>')
    out.append('<p>프로그램 참여와 후원, 연구소 활동에 관해 문의해 주세요.</p>')
    out.append('<p class="contact-address"><a href="mailto:agit.somnium@gmail.com">agit.somnium@gmail.com</a></p>')
    out.append(f'<p><a class="text-link" href="{e(base)}/about/#visit">오시는 길</a></p>')
    out.append('</section>')
    return '\n'.join(out)

def archive_page(content, md, base=''):
    """창립 이후 프로그램을 해마다 모은 쪽. content/archive.md 를 그대로 옮긴다."""
    body = clean_content(content.get('archive.md', ''))
    return (page_intro('지난 프로그램', '2017년 창립부터 지금까지, 솜니움이 함께 공부한 시간입니다.', base)
            + '<div class="prose archive-prose">' + md(body) + '</div>')
