#!/usr/bin/env python3
"""Build the private board activity report (활동평가·계획) from a JSON data file.
The data file is written by people (counts, assessments, plans); this only validates the shape, refuses contact details, and embeds it in the fixed template."""
import argparse, hashlib, html, json, re
from pathlib import Path

VERSION = 'somnium-activity-paper/1'
CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"
KINDS = ('세미나', '특강', '북클럽', '연구자초대')


def check(data):
    if data.get('version') != VERSION: raise ValueError('version must be ' + VERSION)
    for key in ('org', 'title', 'period', 'issued', 'author', 'audience'):
        if not isinstance(data.get(key), str) or not data[key].strip(): raise ValueError('missing text: ' + key)
    programs = data.get('programs')
    if not isinstance(programs, list) or not programs: raise ValueError('programs required')
    for p in programs:
        if p.get('kind') not in KINDS: raise ValueError('program kind must be one of %s: %s' % ('/'.join(KINDS), p.get('name')))
        if type(p.get('applied')) is not int or p['applied'] < 0: raise ValueError('applied must be a whole number: %s' % p.get('name'))
        if not isinstance(p.get('assess'), list) or not all(isinstance(a, str) for a in p['assess']): raise ValueError('assess must be a list of lines: %s' % p.get('name'))
        for key in ('name', 'date', 'host', 'mode', 'inflow'):
            if not isinstance(p.get(key), str): raise ValueError('program text missing: %s' % key)
    inflow = data.get('inflowAgg')
    if not isinstance(inflow, dict) or any(type(v) is not int for v in inflow.values()): raise ValueError('inflowAgg must map source to whole numbers')
    if sum(inflow.values()) != sum(p['applied'] for p in programs): raise ValueError('inflow total differs from applied total')
    fin = data.get('finance') or {}
    for side in ('income', 'expense'):
        if not all(isinstance(r, list) and len(r) == 2 and type(r[1]) is int for r in fin.get(side, [])) or not fin.get(side): raise ValueError('finance.%s must be [label, whole number] rows' % side)
    if type(fin.get('carryover')) is not int: raise ValueError('finance.carryover required')
    plan = data.get('plan') or {}
    if not isinstance(plan.get('lineup'), list) or not isinstance((plan.get('network') or {}).get('members'), list): raise ValueError('plan.network.members and plan.lineup required')
    return data


def build(data):
    check(data)
    template = Path(__file__).with_name('activity_paper.html').read_text()
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    # participants' contact details never belong in this report
    if re.search(r'01[016789][- ]?\d{3,4}[- ]?\d{4}|[\w.+-]+@[\w-]+\.[\w.]+', encoded): raise ValueError('possible phone number or e-mail in report data')
    return template.replace('REPORT_CSP', html.escape(CSP, quote=True)).replace('REPORT_JSON', encoded)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True); p.add_argument('--out', required=True); p.add_argument('--manifest')
    a = p.parse_args()
    out = Path(a.out)
    if out.exists(): raise ValueError('choose a new output; preserve earlier versions')
    data = json.loads(Path(a.data).read_text()); body = build(data); out.write_text(body)
    digest = hashlib.sha256(body.encode()).hexdigest()
    if a.manifest:
        mp = Path(a.manifest)
        if mp.exists(): raise ValueError('choose a new manifest path')
        mp.write_text(json.dumps(dict(file=str(out.resolve()), title='솜니움 ' + data['title'], period=data['period'][:80], sha256=digest, member_safe=False, publish=False), ensure_ascii=False, indent=2))
    print(json.dumps({'programs': len(data['programs']), 'applied': sum(x['applied'] for x in data['programs']), 'sha256': digest}, ensure_ascii=False))


if __name__ == '__main__': main()
