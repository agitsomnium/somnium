#!/usr/bin/env python3
"""인스타그램 최신 글(behold.so JSON 피드)을 data/live/instagram.json 으로 저장. 키·토큰 없음.
실패하면 이전 파일을 그대로 두고 0으로 끝난다(빌드를 막지 않음)."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(data):
    posts = data.get('posts', data) if isinstance(data, dict) else data
    out = []
    for p in posts if isinstance(posts, list) else []:
        sizes = p.get('sizes') or {}
        img = ((sizes.get('medium') or {}).get('mediaUrl') or p.get('thumbnailUrl')
               or (p.get('mediaUrl') if p.get('mediaType') != 'VIDEO' else ''))
        link = p.get('permalink', '')
        if not img or not str(link).startswith('https://www.instagram.com/'):
            continue
        cap = (p.get('prunedCaption') or p.get('caption') or '').strip()
        out.append({'image': img, 'link': link, 'caption': cap[:140], 'date': str(p.get('timestamp', ''))[:10]})
    return out[:6]


def main(out_dir='data/live'):
    cfg = json.loads((ROOT / 'config' / 'site.json').read_text(encoding='utf-8'))
    url = ((cfg.get('instagram') or {}).get('behold_feed_url') or '').strip()
    target = ROOT / out_dir / 'instagram.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not url.startswith('https://feeds.behold.so/'):
        print('인스타 피드 주소 없음 — 건너뜀')
        if not target.exists():
            target.write_text('[]', encoding='utf-8')
        return 0
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'somnium-site'}), timeout=20) as r:
            posts = normalize(json.loads(r.read().decode('utf-8')))
    except Exception as exc:
        print('인스타 최신 글 받기 실패(이전 목록 유지): %s' % exc)
        if not target.exists():
            target.write_text('[]', encoding='utf-8')
        return 0
    target.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding='utf-8')
    print('인스타 최신 글 %d개 저장' % len(posts))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
