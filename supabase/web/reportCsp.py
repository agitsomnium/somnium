"""Permit only the exact bundled finance-paper code/style in sandboxed srcdoc documents.
srcdoc documents inherit their creator CSP; the fixed hashes avoid allowing arbitrary inline scripts.
"""
import base64
import hashlib
import re
from pathlib import Path


def paper_csp():
    source = (Path(__file__).resolve().parent.parent / 'ops/accounting_paper.html').read_text()
    code = re.findall(r'<script>([\s\S]*?)</script>', source)[0]
    css = re.findall(r'<style>([\s\S]*?)</style>', source)[0]
    digest = lambda value: base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
    return "script-src 'self' 'sha256-" + digest(code) + "'; style-src 'self' 'sha256-" + digest(css) + "'; style-src-attr 'unsafe-inline'"
