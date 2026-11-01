"""Recount member-visible lectures from a connected-lecture catalog JSON (aggregate output only).

Mirrors the publish rule in migrations/20261031182424_lectures_only.sql: titles matching the Q&A
pattern (including the spaced form '질의 응답') cannot be published.
This reads a local source file, not the hosted database. It does not prove the hosted count.
"""
import argparse
import json
import re
import unicodedata
from collections import Counter

QA = re.compile(r'질의\s*응답|질문\s*(?:과|및|&)?\s*(?:답변|응답)|(?<![0-9A-Za-z가-힣])q\s*(?:&|and|n|/)\s*a(?![0-9A-Za-z가-힣])', re.I)


def recount(rows):
    nfc = lambda value: unicodedata.normalize('NFC', value)
    hidden = [r for r in rows if QA.search(nfc(r['title']))]
    exact = [r for r in hidden if '질의응답' in nfc(r['title'])]
    visible = [r for r in rows if not QA.search(nfc(r['title']))]
    return {
        'source_rows': len(rows),
        'unique_video_ids': len({r['video_id'] for r in rows}),
        'hidden_qa_exact': len(exact),
        'hidden_qa_spaced_only': len(hidden) - len(exact),
        'hidden_total': len(hidden),
        'visible': len(visible),
        'visible_duplicate_titles': sum(1 for n in Counter(nfc(r['title']) for r in visible).values() if n > 1),
        'series': dict(Counter(r['series_title'] for r in visible).most_common()),
        'scope': 'local source file only; hosted database not queried',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', required=True)
    args = parser.parse_args()
    with open(args.catalog, encoding='utf-8') as f:
        print(json.dumps(recount(json.load(f)), ensure_ascii=False, indent=2))
