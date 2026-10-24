#!/usr/bin/env python3
"""Static site builder for the Somnium institute site."""
import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data import load_tables, validate, public_rows, overrides as data_overrides  # noqa: E402
from render import shell, seminar_detail
from home_plaza import home
from extras import load_videos, load_instagram
import seo
from pages import about_page, program_page, archive_page, participate_page, page_intro  # noqa: E402
from videos_page import videos_page, series_pages  # noqa: E402
import insta_events  # noqa: E402
from extras import today as _today  # noqa: E402

PAGE_DESC = {
    'about': '솜니움 기독교정치사회연구소의 정신과 미션, 이사회, 2017년부터의 연혁, 서울 합정 사무실 오시는 길.',
    'programs': '솜니움의 세미나·북클럽·기획강좌. 정치사회이론과 기독교를 함께 읽는 공부 모임 일정과 신청 안내.',
    'videos': '솜니움 세미나·강좌·북클럽 영상을 최근 순서로 모았습니다. 시리즈는 묶어서 차례대로 볼 수 있습니다.',
    'archive': '2017년 창립 이후 솜니움이 진행한 세미나·강좌·북토크·토론회를 해마다 모았습니다.',
    'participate': '솜니움 프로그램 참여 신청과 후원·참가비 계좌 안내. CMS 정기후원(기부금 영수증) 가능.',
}

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _inline(text):
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        out.append('<a href="%s">%s</a>' % (html.escape(m.group(2), quote=True), html.escape(m.group(1))))
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def markdown(text):
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks, para, items = [], [], []

    def flush():
        if para:
            blocks.append("<p>" + "<br>\n".join(_inline(x) for x in para) + "</p>")
            para.clear()
        if items:
            blocks.append("<ul>" + "".join("<li>%s</li>" % _inline(i) for i in items) + "</ul>")
            items.clear()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush()
            n = len(m.group(1))
            blocks.append("<h%d>%s</h%d>" % (n, _inline(m.group(2).strip()), n))
            continue
        if re.match(r"^\s*-\s+", line):
            if para:
                flush()
            items.append(re.sub(r"^\s*-\s+", "", line))
            continue
        if items:
            flush()
        para.append(line.strip())
    flush()
    return "\n".join(blocks)


def _read(path):
    p = ROOT / "content" / path
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _page(outdir, rel, title, body, base, theme, preview, description='', jsonld=None):
    text = shell(title=title, body=body, base=base, theme=theme, preview=preview)
    full = title if title == '홈' else title + ' | 솜니움 기독교정치사회연구소'
    if title == '홈':
        full = '솜니움 기독교정치사회연구소 — 연구자와 시민이 만나는 광장'
    text = text.replace('</head>', seo.head_tags(rel, full, description, base, jsonld=jsonld) + '\n</head>', 1)
    _write(outdir / rel, text)
    return text




def _swap(stage, target):
    backup = None
    if target.exists():
        backup = Path(tempfile.mkdtemp(prefix=".bak-", dir=str(target.parent)))
        backup.rmdir()
        os.replace(str(target), str(backup))
    try:
        os.replace(str(stage), str(target))
    except Exception:
        if backup is not None and not target.exists():
            os.replace(str(backup), str(target))
        raise
    if backup is not None:
        shutil.rmtree(str(backup), ignore_errors=True)


def _home_videos(data_dir):
    """홈 영상 칸: 오늘 받은 최근 영상, 못 받았으면 누적 목록에서 최근 것."""
    vids = load_videos(data_dir)
    if vids:
        return vids
    from videos_page import load_catalog
    rows = [r for r in load_catalog([]) if r.get('channel') != 'series']
    rows.sort(key=lambda r: r.get('published') or '', reverse=True)
    return rows[:6]


def build(data_dir, outdir, base='', theme='b', preview=False):
    target = Path(outdir)
    if target.is_symlink():
        raise ValueError('target is a symlink: %s' % target)
    resolved = target.resolve()
    root = Path(ROOT).resolve()
    allowed = [root / 'dist', root / 'design']
    ok = False
    for a in allowed:
        a = a.resolve()
        if resolved == a or a in resolved.parents:
            ok = True
            break
    if not ok:
        raise ValueError('target outside allowed roots: %s' % resolved)
    if base != '':
        if not base.startswith('/'):
            raise ValueError('base must start with /')
        if base.endswith('/') or '..' in base or '//' in base or any(c.isspace() for c in base):
            raise ValueError('invalid base: %r' % base)
    if base and not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)+', base):
        raise ValueError('invalid base path')
    target.parent.mkdir(parents=True, exist_ok=True)
    tables = load_tables(data_dir)
    page_over, cfg_over = data_overrides(tables)
    import extras as _ex
    _ex.CONFIG_OVERRIDES.clear()
    _ex.CONFIG_OVERRIDES.update(cfg_over)
    insta_events.merge(tables, load_instagram(data_dir, limit=80), _today())
    tables = validate(tables)
    stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=str(target.parent)))
    try:
        seminars = public_rows(tables, '세미나')
        bookclubs = public_rows(tables, '북클럽')
        videos = public_rows(tables, '영상')
        events = seo.events_jsonld(tables, base)
        _page(stage, 'index.html', '홈', home(tables, base, _home_videos(data_dir), load_instagram(data_dir)), base, theme, preview,
              jsonld=[seo.org_jsonld()] + events)
        for s in seminars:
            sid = str(s.get('id', ''))
            body = seminar_detail(s, tables, base)
            sdesc = ' '.join(x for x in (s.get('제목', ''), s.get('부제', ''), (s.get('소개') or '').split('\n')[0]) if x)
            sev = [ev for ev in events if ('seminars/%s/' % sid) in ev.get('url', '')]
            _page(stage, 'seminars/%s/index.html' % sid, s.get('제목', '세미나'), body, base, theme, preview, sdesc, sev)
        content = {name: page_over.get(name[:-3]) or _read(name) for name in ('about.md','board.md','history.md','visit.md','lectures.md','agit.md','participate.md','archive.md','people.md')}
        for slug, title, body in (
            ('about', '연구소 소개', about_page(content, markdown, base)),
            ('programs', '프로그램', program_page(tables, content, markdown, base)),
            ('videos', '유튜브', videos_page(load_videos(data_dir), page_intro, base)),
            ('archive', '지난 프로그램', archive_page(content, markdown, base)),
            ('participate', '참여·후원', participate_page(tables, content, markdown, base)),
        ):
            _page(stage, slug + '/index.html', title, body, base, theme, preview, PAGE_DESC.get(slug, ''))
        vpages = series_pages(load_videos(data_dir), page_intro, base)
        for path, title, body, desc in vpages:
            _page(stage, path, title, body, base, theme, preview, desc)
        assets_src = Path(ROOT) / 'assets'
        if assets_src.is_dir():
            shutil.copytree(str(assets_src), str(stage / 'assets'))
        _page(stage, '404.html', '찾을 수 없음', '<div class="prose"><h1>페이지를 찾을 수 없습니다</h1><p>메뉴에서 원하시는 자료를 찾아 주세요.</p></div>', base, theme, preview)
        _write(stage / '.nojekyll', '')
        _write(stage / 'robots.txt', seo.robots_txt())
        _write(stage / 'llms.txt', seo.llms_txt(tables, base))
        rels = ['index.html'] + ['seminars/%s/' % str(x.get('id', '')) for x in seminars] + [p + '/' for p in ('about', 'programs', 'videos', 'archive', 'participate')] + [x[0][:-len('index.html')] for x in vpages]
        sm = seo.sitemap_xml(rels)
        if sm:
            _write(stage / 'sitemap.xml', sm)
        meta = {'counts': {'seminars': len(seminars), 'bookclubs': len(bookclubs), 'videos': len(videos)}, 'base': base, 'preview': bool(preview)}
        _write(stage / 'build.json', json.dumps(meta, ensure_ascii=False, indent=2))
        _swap(stage, target)
    except Exception:
        shutil.rmtree(str(stage), ignore_errors=True)
        raise
    return target








def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sample', action='store_true')
    group.add_argument('--data')
    parser.add_argument('--output', default=str(Path(ROOT) / 'dist'))
    parser.add_argument('--base', default=os.environ.get('SITE_BASE_PATH', ''))
    parser.add_argument('--theme', default='b', choices=['a', 'b'])
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args(argv)
    if args.sample:
        data_dir = Path(ROOT) / 'data' / 'sample'
        preview = True
    else:
        data_dir = Path(args.data)
        preview = args.preview
    target = build(data_dir, args.output, args.base, args.theme, preview)
    print('built: %s' % target)
    print('sample: %s' % bool(args.sample))
    return 0


if __name__ == "__main__":
    main()
