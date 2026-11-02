"""Render the pre-signup guide (/guide/) from guide/guide-data.json.

--mode review  shows items whose permission is pending, each with a visible badge.
--mode public  drops pending items. It never reads video IDs, URLs or private catalog data.
"""
import argparse
import json
from html import escape
from pathlib import Path

WEB = Path(__file__).resolve().parent
DATA = WEB / 'guide/guide-data.json'


def esc(value):
    return escape(str(value), quote=True)


def paragraphs(value):
    return '<br>'.join(esc(part) for part in str(value).split('\n'))


def render(data, mode):
    review = mode == 'review'
    out = []
    add = out.append
    hero = dict(data['hero'])
    count_label = f'지난 강의 {data["memberLectures"]["count"]}편' if data['memberLectures']['verified'] else '지난 강의'
    hero['lead'] = hero['lead'].replace('{lecture_count}', count_label)
    add('<!doctype html><html lang="ko" class="theme-b"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow,noarchive">'
        '<title>후원회원 안내 | 솜니움</title>'
        '<link rel="stylesheet" href="/brand.css"><link rel="stylesheet" href="/assets/brand.css">'
        '<link rel="stylesheet" href="/tokens.css"><link rel="stylesheet" href="/fonts-display.css">'
        '<link rel="stylesheet" href="/trial.css"><link rel="stylesheet" href="/member.css">'
        '<link rel="stylesheet" href="/guide.css"><script src="/navigation.js" defer></script></head><body>')
    add('<a class="skip-link" href="#main">본문으로</a>')
    if review:
        add('<div class="trial-banner">운영진 검토본 · 공개 전 운영진 확인이 필요한 항목에는 표시가 붙어 있습니다.</div>')
    add('<header class="site-header"><div class="header-inner"><a class="logo" href="https://somniumagit.com">'
        '<img src="/assets/somnium_wordmark_on_paper.svg" width="75" height="48" alt="솜니움">'
        '<span>솜니움<br>기독교정치사회연구소</span></a><nav class="site-nav" aria-label="주요 메뉴">'
        '<a class="classroom-link" href="/guide/" aria-current="page">후원회원 안내</a><a href="/?entry=login#entry">강의실 로그인</a>'
        '<a href="https://somniumagit.com/participate/">참여·후원</a></nav></div></header>')
    add('<nav class="page-navigation" aria-label="페이지 이동"><button type="button" data-page-back data-back-home="https://somniumagit.com/">← 뒤로가기</button><a href="https://somniumagit.com">홈으로</a><a href="/">강의실 첫 화면</a></nav>')
    add('<main class="container guide" id="main">')
    add(f'<div class="intro"><p class="eyebrow">{esc(hero["eyebrow"])}</p><h1>{paragraphs(hero["title"])}</h1>'
        f'<p>{esc(hero["lead"])}</p><div class="guide-cta">'
        '<a class="cta primary" href="/?entry=signup#entry">회원가입 시작하기</a>'
        '<a class="cta" href="/?entry=login#entry">이미 가입했어요 · 로그인</a></div></div>')

    add('<section id="paths" aria-labelledby="paths-h"><h2 id="paths-h">어디로 가면 될까요?</h2><div class="path-grid">')
    targets = {'new': '/?entry=signup#entry', 'member': '/?entry=login#entry', 'code': '/?entry=login#entry'}
    for item in data['paths']:
        add(f'<a class="path-card" href="{targets[item["id"]]}"><strong>{esc(item["title"])}</strong>'
            f'<span>{esc(item["body"])}</span></a>')
    add('</div></section>')

    add('<section id="benefits" aria-labelledby="ben-h"><h2 id="ben-h">월 1만 원 이상 후원회원의 이용 혜택</h2><div class="card-grid">')
    for item in data['benefits']:
        add(f'<article class="card"><h3>{esc(item["title"])}</h3><p>{esc(item["body"])}</p></article>')
    add('</div></section>')

    count = data['memberLectures']
    if count['verified']:
        intro = f'후원회원 강의실에는 지금 회원 강의 {esc(count["count"])}편이 있습니다. 대표 시리즈입니다.'
    else:
        intro = '지난 세미나와 특강을 모아 둔 대표 시리즈입니다.'
        if review:
            intro += f' <span class="badge">편수 {esc(count["count"])}편은 원격 실조회 전 · 공개 안내에는 숫자를 쓰지 않음</span>'
    add('<section id="series" aria-labelledby="ser-h"><h2 id="ser-h">어떤 강의가 있나요</h2>'
        f'<p class="muted">{intro}</p><div class="series-list">')
    for s in data['series']:
        pending = s['permission'] != 'public'
        add('<article class="series-card"><h3>' + esc(s['name']) + '</h3>'
            f'<p class="when">{esc(s["when"])}' + (' · 회차 자료 있음' if s.get('materials') else '') + '</p>'
            f'<p>{esc(s["theme"])}</p>')
        if s.get('lecturers'):
            if not pending:
                add(f'<p class="who">강사 {esc(s["lecturers"])}</p>')
            elif review:
                add(f'<p class="who">강사 {esc(s["lecturers"])} <span class="badge">강사 공개 허락 확인 전 · 공개 때 빠짐</span></p>')
        add('</article>')
    add('</div></section>')

    add('<section id="start" aria-labelledby="start-h"><h2 id="start-h">가입부터 강의 이용까지</h2><ol class="flow">')
    for step in data['flow']:
        add(f'<li><span class="num" aria-hidden="true">{step["n"]}</span><div><h3>{esc(step["title"])}</h3><p>{esc(step["body"])}</p>')
        if step.get('link'):
            link = step['link']
            external = link['href'].startswith('http')
            rel = ' rel="noopener noreferrer" target="_blank"' if external else ''
            add(f'<a class="cta{" primary" if step["n"] == 1 else ""}" href="{esc(link["href"])}"{rel}>{esc(link["label"])}</a>')
        add('</div></li>')
    add('</ol></section>')


    add('<section id="activities" aria-labelledby="act-h"><h2 id="act-h">후원금이 이어 가는 일</h2>'
        '<p class="muted">솜니움이 지금 하고 있는 활동입니다. 후원은 이 공부의 자리를 계속 열어 두는 데 쓰입니다.</p><div class="card-grid">')
    for item in data['activities']:
        add(f'<article class="card"><h3>{esc(item["title"])}</h3><p>{esc(item["body"])}</p></article>')
    add('</div></section>')

    order = data['order']
    if order['approved'] or review:
        add('<section id="order" aria-labelledby="ord-h"><h2 id="ord-h">처음이라면 이 순서로</h2>')
        if review and not order['approved']:
            add(f'<p><span class="badge">{esc(order["status"])} · 공개 안내에서는 이 절이 빠짐</span></p>')
        add('<ol class="order-list">')
        for step in order['steps']:
            add(f'<li><strong>{esc(step["series"])}</strong><span>{esc(step["why"])}</span></li>')
        add('</ol></section>')

    vis = data['visibility']
    add('<section id="visibility" aria-labelledby="vis-h"><h2 id="vis-h">누구에게 열려 있나요</h2><div class="two-col">'
        '<div><h3>누구나 볼 수 있는 것</h3><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in vis['open'] if order['approved'] or review or '추천' not in x) + '</ul></div>'
        '<div><h3>후원회원·수강 코드 이용자에게만 열리는 것</h3><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in vis['members']) + '</ul></div></div>'
        f'<p class="muted">{esc(vis["tasterNote"])}</p></section>')

    add('<section id="faq" aria-labelledby="faq-h"><h2 id="faq-h">자주 묻는 질문</h2>')
    for item in data['faq']:
        add(f'<details><summary>{esc(item["q"])}</summary><p>{esc(item["a"])}</p></details>')
    add('</section></main>')
    add('<footer class="site-footer"><div class="container"><p>후원·기부금 처리는 한빛누리의 기존 절차를 따릅니다.<br>'
        '이 페이지는 후원회원 강의 이용 안내입니다.</p><a href="mailto:agit.somnium@gmail.com">agit.somnium@gmail.com</a></div></footer>')
    add('</body></html>')
    return ''.join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['review', 'public', 'all'], default='review')
    parser.add_argument('--out-dir', type=Path, default=WEB / 'dist')
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding='utf-8'))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for mode in (['review', 'public'] if args.mode == 'all' else [args.mode]):
        target = args.out_dir / f'guide-{mode}.html'
        target.write_text(render(data, mode), encoding='utf-8')
        print(target)


if __name__ == '__main__':
    main()
