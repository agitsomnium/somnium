import html
from html import escape as e
from data import public_rows


def shell(title, body, base='', theme='a', preview=False):
    t = e(title)
    theme_cls = 'theme-b' if theme == 'b' else 'theme-a'
    banner = ''
    if preview:
        banner = '<div class="preview-banner" role="note">' + e('검토용 시안 · 일정과 신청 정보는 원문 확인 중입니다.') + '</div>'
    nav_items = [('/about/', '연구소 소개'), ('/programs/', '프로그램'), ('/resources/', '연구자료'), ('/participate/', '참여·후원')]
    nav = ''.join('<li><a href="' + e(base + p) + '">' + e(l) + '</a></li>' for p, l in nav_items)
    return (
        '<!DOCTYPE html>\n<html lang="ko" class="' + theme_cls + '">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>' + t + '</title>\n'
        '<meta name="description" content="' + e('연구자와 시민이 함께 배우고 토론하는 공부 모임 SOMNIUM') + '">\n'
        '<link rel="stylesheet" href="' + e(base + '/assets/site.css') + '">\n'
        '</head>\n<body>\n'
        + banner +
        '<a class="skip-link" href="#main">' + e('본문으로 건너뛰기') + '</a>\n'
        '<header class="site-header">\n'
        '<a class="logo" href="' + e(base + '/') + '">SOMNIUM <span class="ko">' + e('솜니움') + '</span></a>\n'
        '<nav aria-label="' + e('주요 메뉴') + '"><ul>' + nav + '</ul></nav>\n'
        '</header>\n'
        '<main id="main">\n' + body + '\n</main>\n'
        '<footer class="site-footer">\n'
        '<p>' + e('문의') + ': <a href="mailto:agit.somnium@gmail.com">agit.somnium@gmail.com</a></p>\n'
        '<p><a href="https://somnium.oopy.io">' + e('이전 사이트') + '</a></p>\n'
        '</footer>\n</body>\n</html>'
    )


def _status(s):
    return e((s or '').strip() or '일정 확인 중')


def home(tables, base=''):
    seminars = public_rows(tables, '세미나')
    books = public_rows(tables, '북클럽')
    notices = public_rows(tables, '공지')
    videos = public_rows(tables, '영상')
    out = []
    out.append('<section class="hero">')
    out.append('<div><h1>' + '연구자와 시민이<br>만나는 광장' + '</h1>')
    out.append('<p>' + e('함께 배우고, 토론하며, 꿈을 꿉니다.') + '</p></div>')
    out.append('<div class="questions"><h2>' + e('우리가 함께 묻는 것') + '</h2><ol>')
    for q in ['오늘의 자본주의는 일과 삶을 어떻게 바꾸고 있을까요?',
              '기독교는 어떤 시민의 삶을 만들 수 있을까요?',
              '이론이 놓치는 주변부의 경험은 무엇일까요?',
              '함께 공부하는 일은 어떤 변화를 만들 수 있을까요?']:
        out.append('<li>' + e(q) + '</li>')
    out.append('</ol></div></section>')
    out.append('<section class="intro"><h2>' + e('읽고, 묻고, 함께 연구합니다') + '</h2>')
    out.append('<p>' + e('정치사회이론을 함께 읽고, 연구자와 시민이 질문을 나누며 토론합니다.') + '</p></section>')
    out.append('<section class="section"><h2>' + e('지금 함께하는 공부') + '</h2>')
    if seminars:
        first = seminars[0]
        fid = str(first.get('id', ''))
        out.append('<div class="program-grid"><article class="program-featured">')
        out.append('<a href="' + e(base + '/seminars/' + fid + '/') + '">')
        out.append('<img class="banner" src="' + e(base + '/assets/research.jpg') + '" alt="' + e('솜니움 연구소') + '" width="1200" height="400" loading="lazy">')
        out.append('</a>')
        out.append('<p class="status">' + _status(first.get('상태')) + '</p>')
        out.append('<h3><a href="' + e(base + '/seminars/' + fid + '/') + '">' + e(first.get('제목', '')) + '</a></h3>')
        if first.get('부제'):
            out.append('<p class="subtitle">' + e(first.get('부제')) + '</p>')
        out.append('<p><a href="' + e(base + '/seminars/' + fid + '/') + '">' + e('자세히 보기') + '</a></p>')
        out.append('</article></div>')
        rest = seminars[1:]
        if rest:
            out.append('<ul class="program-list">')
            for s in rest:
                out.append('<li class="program-row"><a href="' + e(base + '/seminars/' + str(s.get('id', '')) + '/') + '">' + e(s.get('제목', '')) + '</a> <span class="status">' + _status(s.get('상태')) + '</span></li>')
            out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('현재 공개된 세미나가 없습니다.') + '</p>')
    if books:
        out.append('<h3>' + e('독서 모임') + '</h3><ul class="book-list">')
        for b in books:
            line = '<li>' + e(b.get('도서', '')) + ' · ' + e(b.get('제목', '')) + ' <span class="status">' + _status(b.get('상태')) + '</span>'
            url = (b.get('신청_url') or '').strip()
            if b.get('상태') in ('모집중', '진행중') and url:
                line += ' <a href="' + e(url) + '">' + e('신청하기') + '</a>'
            out.append(line + '</li>')
        out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('현재 공개된 독서 모임이 없습니다.') + '</p>')
    out.append('</section>')
    out.append('<section class="section"><h2>' + e('소식과 기록') + '</h2>')
    if notices:
        out.append('<ul class="notice-list">')
        for n in notices:
            url = (n.get('링크_url') or '').strip()
            title = e(n.get('제목', ''))
            if url:
                title = '<a href="' + e(url) + '">' + title + '</a>'
            out.append('<li>' + title + ' <span class="body">' + e(n.get('본문', '')) + '</span></li>')
        out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('등록된 소식이 없습니다.') + '</p>')
    if videos:
        out.append('<ul class="video-list">')
        for v in videos:
            url = (v.get('youtube_url') or '').strip()
            if url:
                out.append('<li><a href="' + e(url) + '">' + e(v.get('제목', '')) + '</a></li>')
            else:
                out.append('<li>' + e(v.get('제목', '')) + '</li>')
        out.append('</ul>')
    else:
        out.append('<p class="empty">' + e('등록된 영상이 없습니다.') + '</p>')
    out.append('<p><a href="' + e(base + '/resources/') + '">' + e('자료 모아보기') + '</a></p>')
    out.append('</section>')
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