#!/usr/bin/env python3
"""유튜브 채널 RSS(최근 15개)를 받아 data/live/youtube.json 으로 저장. 키 필요 없음.
실패하면 이전 파일을 그대로 두고 0으로 끝난다(홈페이지 빌드를 막지 않음)."""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def is_short(title, href=''):
    """쇼츠는 홈페이지 수집·표시에서 제외하고 원본 채널에는 남긴다."""
    return bool(re.search(r'#shorts?\b|쇼츠', title or '', re.I)
                or '/shorts/' in (href or '').lower())


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for en in root.findall('a:entry', NS):
        vid = en.findtext('yt:videoId', default='', namespaces=NS)
        title = en.findtext('a:title', default='', namespaces=NS)
        pub = en.findtext('a:published', default='', namespaces=NS)
        link = en.find('a:link', NS)
        href = link.get('href', '') if link is not None else ''
        if vid and not is_short(title, href):
            out.append({'id': vid, 'title': title, 'published': pub[:10]})
    return out


def main(out_dir='data/live'):
    cfg = json.loads((ROOT / 'config' / 'site.json').read_text(encoding='utf-8'))
    chans = [cfg.get('youtube') or {}] + list(cfg.get('youtube_more') or [])
    chans = [ch for ch in chans if ch.get('channel_id')]
    target = ROOT / out_dir / 'youtube.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not chans:
        print('channel_id 없음 — 건너뜀')
        return 0
    videos, failed = [], 0
    for ch in chans:
        url = 'https://www.youtube.com/feeds/videos.xml?channel_id=' + ch['channel_id']
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'somnium-site'}), timeout=20) as r:
                for v in parse(r.read()):
                    v['channel'] = 'series' if ch is not chans[0] and ch.get('구분') else 'main'
                    videos.append(v)
        except Exception as exc:  # 네트워크 실패는 빌드를 막지 않는다
            failed += 1
            print('유튜브 목록 받기 실패(%s): %s' % (ch.get('이름', ''), exc))
    if failed == len(chans):
        if not target.exists():
            target.write_text('[]', encoding='utf-8')
        return 0
    videos.sort(key=lambda v: v.get('published', ''), reverse=True)
    target.write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding='utf-8')
    print('유튜브 영상 %d개 저장' % len(videos))
    cat = ROOT / 'data' / 'catalog' / 'youtube.json'
    try:
        old = json.loads(cat.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = []
    known = {r.get('id') for r in old}
    new = [v for v in videos if v['id'] not in known]
    if new:
        cat.parent.mkdir(parents=True, exist_ok=True)
        cat.write_text(json.dumps(new + old, ensure_ascii=False, indent=1), encoding='utf-8')
        print('누적 영상 목록에 %d개 추가' % len(new))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
