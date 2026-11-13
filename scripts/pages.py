import re
from extras import MEMBER_LECTURE_COUNT, accounts_block, board_frame, fmt_days
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
    toc = [('spirit', '솜니움의 정신'), ('board', '이사회'), ('past-programs', '지난 프로그램'), ('history', '걸어온 길'), ('people', '함께한 사람들'), ('visit', '오시는 길')]
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
        + '<section id="past-programs"><h2>지난 프로그램</h2>'
        + '<p>지난 공부를 영상으로 다시 만나 보세요. 월 1만 원 이상 정기후원으로 회원 강의와 자료를 이용할 수 있습니다.</p>'
        + '<p><a class="button" href="https://somnium-classroom.pages.dev/guide/">후원회원 강의 둘러보기 →</a> <a class="text-link" href="' + b + '/videos/">유튜브 공개 강의 보기 ↗</a></p>'
        + '<details class="archive-fold"><summary>연도별 프로그램 기록</summary>' + md(clean_content(content.get('archive.md', ''))) + '<h3>기획강좌·특강</h3>' + md(clean_content(content.get('lectures.md', ''))) + '</details></section>'
        + '<section id="agit"><h2>아지트솜니움</h2>' + md(clean_content(content.get('agit.md', ''))) + '</section>'
        + '<section id="people"><h2>함께한 사람들</h2>' + md(people) + '</section>'
        + '<section id="visit"><h2>오시는 길</h2>' + md(visit)
        + '<figure><img src="' + b + '/assets/visit-building.webp" width="1196" height="900" loading="lazy" alt="솜니움 사무실이 있는 건물"></figure>'
        + '<p><a href="https://map.naver.com/p/search/%EC%84%9C%EC%9A%B8%20%EB%A7%88%ED%8F%AC%EA%B5%AC%20%EB%8F%85%EB%A7%89%EB%A1%9C%2043" target="_blank" rel="noopener">네이버지도에서 길찾기↗</a></p>'
        + '</section>'
        + '</article>'
        + '</div>'
    )



def public_seminar_videos(base=''):
    """Curated public seminar videos; member-only catalog entries never appear."""
    import json
    from pathlib import Path
    from videos_page import load_catalog
    programs = json.loads((Path(__file__).resolve().parents[1] / 'config/program-videos.json').read_text(encoding='utf-8'))
    public = {row['id']: row for row in load_catalog()}
    out = []
    for program in programs:
        videos = [public[vid] for vid in program['video_ids'] if vid in public]
        if not videos:
            continue
        out.append('<div class="public-seminar"><h3>%s</h3><p>%s</p><div class="yt-grid">' % (e(program['title']), e(program['description'])))
        for row in videos:
            vid = e(row['id'])
            out.append('<a class="yt-card" href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener"><img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" width="480" height="360" loading="lazy" alt=""><strong>%s</strong><span>유튜브에서 강의 보기 ↗</span></a>' % (vid, vid, e(row['title'])))
        out.append('</div></div>')
    return ''.join(out)


def program_page(tables, content, md, base=''):
    from extras import today
    base = _base(base)
    books = public_rows(tables, '북클럽')
    live_books = [r for r in books if r.get('상태') in ('모집중', '진행중')]
    imgs = {'book-october': 'assets/sonjeol.webp', 'book-november': 'assets/bookclub-close-poster.jpg', 'book-november-love': 'assets/bookclub-love-poster.jpg'}
    out = ['<div class="program-page">', '<header class="program-heading"><h1>%s월 북클럽</h1></header>' % today().month]
    out.append('<section id="bookclubs" aria-label="진행·모집 중인 북클럽"><div class="book-listing">')
    for r in live_books:
        bid, title = r['id'], r.get('도서') or r.get('제목') or ''
        out.append('<article class="book-program" id="book-%s">' % e(bid))
        if bid in imgs:
            out.append('<aside class="book-cover"><img src="%s/%s" width="864" height="1080" loading="eager" alt="%s 북클럽 포스터"></aside>' % (e(base), e(imgs[bid]), e(title)))
        out.append('<div class="book-copy"><h2>%s</h2>' % e(title))
        schedule = ' · '.join(x for x in (fmt_days(r.get('날짜') or ''), r.get('시간')) if x)
        out.append('<p class="book-schedule">%s</p>' % e(schedule))
        if r.get('신청_url'):
            out.append('<a class="button book-apply" href="%s" aria-label="%s 북클럽 신청하기">신청하기 ↗</a>' % (e(r['신청_url']), e(title)))
        else:
            out.append('<a class="text-link" href="mailto:agit.somnium@gmail.com">참여 문의 ↗</a>')
        out.append('<details class="book-details"><summary>모임 소개·장소</summary>')
        if r.get('소개'):
            out.append('<p>%s</p>' % e(r['소개']))
        if r.get('장소'):
            out.append('<p>장소: %s</p>' % e(r['장소']))
        if r.get('참가비'):
            out.append('<p>참가비: %s</p>' % e(r['참가비']))
        out.append('</details></div></article>')
    if not live_books:
        out.append('<p>지금 모집 중인 북클럽이 없습니다. 아래에서 공개 강의와 후원회원 강의를 만나 보세요.</p>')
    out.append('</div></section>')
    out.append('<section class="member-invitation" id="member-lectures"><h2>월 1만 원 후원으로, 지난 강의를 다시</h2>')
    out.append('<p>현대 자본주의 세미나 전체 6강과 솜니움의 지난 강의·자료를 보실 수 있습니다.</p>')
    out.append('<a class="button" href="https://somnium-classroom.pages.dev/guide/">후원회원 강의 둘러보기 →</a></section>')
    out.append('<section class="content-section" id="seminars"><div class="section-head"><h2>세미나 · 공개 강의</h2><p>공개된 강의로 먼저 만나 보세요.</p></div>')
    out.append(public_seminar_videos(base))
    out.append('</section><p class="program-history-link"><a href="%s/about/#past-programs">연구소 소개에서 지난 프로그램 기록 보기 →</a></p></div>' % e(base))
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

def bookclub_labels(rows):
    """북클럽 (줄, 보일 이름) 목록을 날짜순으로. «11월 북클럽 1/2» 같은 번호는 날짜 차례로 다시 매기고,
    책 제목(도서 칸)이 있으면 『책』을 덧붙인다."""
    def first_day(r):
        return (str(r.get('날짜') or '').split(';')[0]).strip() or '9999-12-31'
    ordered = sorted(rows, key=first_day)
    stem = lambda r: re.match(r'^(\d+월 북클럽)(?:\s*\d+)?$', str(r.get('제목') or '').strip())
    groups = {}
    for r in ordered:
        m = stem(r)
        if m:
            groups.setdefault(m.group(1), []).append(r)
    out = []
    for r in ordered:
        title = str(r.get('제목') or '').strip()
        m = stem(r)
        if m and len(groups[m.group(1)]) > 1:
            title = '%s %d' % (m.group(1), groups[m.group(1)].index(r) + 1)
        book = str(r.get('도서') or '').strip()
        if book:
            title = '%s · 『%s』' % (title, book)
        out.append((r, title))
    return out


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
    for b, label in bookclub_labels(public_rows(tables, '북클럽') or []):
        state = b.get('상태')
        if state not in active:
            continue
        bid = b.get('id')
        title = label
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
    out.append('<section class="content-section"><h2>후원회원 강의실</h2><p>월 1만 원 이상 정기후원하시면 지난 강의 %d편과 등록된 강의자료를 이용할 수 있습니다. 이메일로 가입한 뒤 후원 신청을 알려 주시면 운영자가 확인해 승인합니다.</p><p><a href="https://somnium-classroom.pages.dev/guide/">강의·후원 안내</a> · <a href="https://somnium-classroom.pages.dev/?entry=signup#entry">회원가입</a> · <a href="https://somnium-classroom.pages.dev/?entry=login#entry">로그인</a></p></section>' % MEMBER_LECTURE_COUNT)
    out.append('<section class="content-section"><h2>회계 보고·기부금영수증</h2><p>회계 보고서는 관리자와 이사 자격 회원만 열람할 수 있습니다.</p><p><a class="text-link" href="https://somnium-classroom.pages.dev/#accounting-panel">회계 보고(이사 전용)</a> · <a class="text-link" href="https://mrmweb.hsit.co.kr/v2/?server=OB24ScQzNnMeOyh7ApK%2BSw==&amp;action=receiptedit" target="_blank" rel="noopener noreferrer">한빛누리 기부금영수증 ↗</a></p></section>')
    out.append('<section id="support" class="content-section"><h2>연구소를 후원하기</h2>')
    out.append('<p>솜니움은 한빛누리 공익기금 Bright Fund를 통해 정기후원을 받고 있습니다. 세미나 참가비도 아래 계좌로 보내 주시면 됩니다.</p>')
    out.append(accounts_block('후원·참가비 계좌'))
    out.append('<p class="source-note">기부금 영수증과 후원 절차는 한빛누리 안내를 확인해 주세요.</p>')
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
            + '<p><a class="button" href="https://somnium-classroom.pages.dev/guide/">월 1만 원 후원 · 회원 강의 둘러보기 →</a> <a class="text-link" href="' + e(base) + '/videos/">유튜브 공개 강의 보기 ↗</a></p><p><a href="' + e(base) + '/about/#past-programs">연구소 소개 · 지난 프로그램 →</a></p>'
            + '<div class="prose archive-prose">' + md(body) + '</div>')
