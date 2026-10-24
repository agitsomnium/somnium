"""책 표지를 내려받아 assets/covers/<북클럽 id>.jpg 로 둔다 (배포 때마다, 키 필요 없음).

표지 주소는 config/site.json 의 "covers" 에 {북클럽 고유이름: 이미지 주소} 로 적는다.
못 받으면 그 카드는 표지 없이 그린다.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT / 'config' / 'site.json').read_text(encoding='utf-8'))
    covers = cfg.get('covers') or {}
    out = ROOT / 'assets' / 'covers'
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for bid, url in covers.items():
        if not url.startswith('https://'):
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (somnium site build)'})
            data = urllib.request.urlopen(req, timeout=20).read()
            if len(data) < 2000 or data[:2] != b'\xff\xd8':
                raise ValueError('표지 그림이 아님')
            (out / (bid + '.jpg')).write_bytes(data)
            ok += 1
        except Exception as ex:  # 표지 하나 못 받아도 배포는 계속
            print('표지 못 받음', bid, ex, file=sys.stderr)
    print('표지 %d/%d' % (ok, len(covers)))


if __name__ == '__main__':
    main()
