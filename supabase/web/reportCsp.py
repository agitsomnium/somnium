"""Permit only the exact bundled finance-paper and activity-paper code/style in sandboxed srcdoc documents.
srcdoc documents inherit their creator CSP; the fixed hashes avoid allowing arbitrary inline scripts.
"""
import base64
import hashlib
import re
from pathlib import Path


PAPERS = ('accounting_paper.html', 'activity_paper.html')


def paper_csp():
    digest = lambda value: base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
    code, css = [], []
    for name in PAPERS:
        source = (Path(__file__).resolve().parent.parent / 'ops' / name).read_text()
        scripts = re.findall(r'<script>([\s\S]*?)</script>', source)
        styles = re.findall(r'<style>([\s\S]*?)</style>', source)
        if len(scripts) != 1 or len(styles) != 1:
            raise ValueError('one inline script and one style expected: ' + name)
        code.append("'sha256-" + digest(scripts[0]) + "'"); css.append("'sha256-" + digest(styles[0]) + "'")
    return "script-src 'self' " + ' '.join(code) + "; style-src 'self' " + ' '.join(css) + "; style-src-attr 'unsafe-inline'"
