#!/usr/bin/env python3
"""인스타그램 최신 글(behold.so JSON 피드)을 data/live/instagram.json 으로 저장. 키·토큰 없음.
실패하면 이전 파일을 그대로 두고 0으로 끝난다(빌드를 막지 않음)."""
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def is_short_video(post):
    """새 피드와 기존 누적 목록의 릴스·쇼츠를 같은 기준으로 제외한다."""
    link = post.get("permalink") or post.get("link") or ""
    parts = urlsplit(str(link)).path.lower().split("/")
    return (any(part in ("reel", "reels", "shorts") for part in parts)
            or str(post.get("mediaProductType", "")).upper() in ("REEL", "REELS")
            or str(post.get("mediaType", "")).upper() in ("VIDEO", "REEL", "REELS"))


def normalize(data):
    posts = data.get('posts', data) if isinstance(data, dict) else data
    out = []
    for p in posts if isinstance(posts, list) else []:
        if is_short_video(p):
            continue
        sizes = p.get('sizes') or {}
        img = ((sizes.get('medium') or {}).get('mediaUrl') or p.get('thumbnailUrl')
               or (p.get('mediaUrl') if p.get('mediaType') != 'VIDEO' else ''))
        link = p.get('permalink', '')
        if not img or not str(link).startswith('https://www.instagram.com/'):
            continue
        cap = (p.get('prunedCaption') or p.get('caption') or '').strip()
        out.append({'image': img, 'link': link, 'caption': cap[:140], 'text': (p.get('caption') or cap)[:4000],
                    'date': str(p.get('timestamp', ''))[:10]})
    return out


def _fallback(target):
    """새로 못 받으면 누적 목록을 그대로 쓴다(없으면 빈 목록)."""
    catalog = ROOT / 'data' / 'catalog' / 'instagram.json'
    if catalog.exists():
        target.write_text(catalog.read_text(encoding='utf-8'), encoding='utf-8')
    elif not target.exists():
        target.write_text('[]', encoding='utf-8')


def main(out_dir='data/live'):
    cfg = json.loads((ROOT / 'config' / 'site.json').read_text(encoding='utf-8'))
    url = ((cfg.get('instagram') or {}).get('behold_feed_url') or '').strip()
    target = ROOT / out_dir / 'instagram.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not url.startswith('https://feeds.behold.so/'):
        print('인스타 피드 주소 없음 — 건너뜀')
        _fallback(target)
        return 0
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'somnium-site'}), timeout=20) as r:
            posts = normalize(json.loads(r.read().decode('utf-8')))
    except Exception as exc:
        print('인스타 최신 글 받기 실패(이전 목록 유지): %s' % exc)
        _fallback(target)
        return 0
    # 무료 피드는 최근 6개만 주므로, 받은 글을 누적 목록(data/catalog/instagram.json)에 쌓아 둔다
    catalog = ROOT / 'data' / 'catalog' / 'instagram.json'
    try:
        old = json.loads(catalog.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = []
    seen = {p['link'] for p in posts}
    merged = posts + [p for p in old if isinstance(p, dict) and p.get('link') not in seen]
    merged.sort(key=lambda p: p.get('date', ''), reverse=True)
    merged = merged[:80]
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding='utf-8')
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding='utf-8')
    print('인스타 새 글 %d개 받음 · 누적 %d개' % (len(posts), len(merged)))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
