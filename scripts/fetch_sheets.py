import argparse
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import SCHEMA, load_tables, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 5 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; fetch_sheets/1.0)"


def _valid_url(url):
    if not isinstance(url, str) or not url or any(c.isspace() for c in url):
        return False
    try:
        p = urllib.parse.urlsplit(url)
        port = p.port
    except Exception:
        return False
    if p.scheme != "https" or p.netloc != "docs.google.com":
        return False
    if p.username or p.password or port is not None or p.fragment:
        return False
    if p.query:
        q = urllib.parse.parse_qs(p.query, keep_blank_values=True)
        gid = q.get("gid")
        if not gid or not gid[0].isdigit():
            return False
    else:
        return False
    parts = [x for x in p.path.split("/") if x != ""]
    if len(parts) == 5 and parts[0] == "spreadsheets" and parts[1] == "d" and parts[2] == "e" and parts[3] and parts[4] == "pub":
        q = urllib.parse.parse_qs(p.query, keep_blank_values=True)
        return q.get("output") == ["csv"] and bool(q.get("gid")) and q["gid"][0].isdigit()
    if len(parts) == 4 and parts[0] == "spreadsheets" and parts[1] == "d" and parts[2] and parts[3] == "export":
        q = urllib.parse.parse_qs(p.query, keep_blank_values=True)
        return q.get("format") == ["csv"] and bool(q.get("gid")) and q["gid"][0].isdigit()
    return False


def fetch_csv(url):
    if not _valid_url(url):
        raise ValueError("invalid spreadsheet CSV URL")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" in ctype or "text/html" in ctype:
            raise ValueError("unexpected HTML response")
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("response exceeds 5MB")
    if not data:
        raise ValueError("empty response")
    text = data.decode("utf-8-sig")
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError("HTML/login response rejected")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or not rows[0]:
        raise ValueError("invalid or empty CSV")
    return text


def _safe_outdir(outdir):
    try:
        raw = Path(outdir)
    except Exception:
        return False
    if raw.is_symlink():
        return False
    try:
        resolved = raw.resolve()
    except Exception:
        return False
    data_dir = (ROOT / "data").resolve()
    target = (ROOT / "data" / "live").resolve()
    if resolved != target:
        return False
    if resolved.parent != data_dir:
        return False
    if resolved.exists() and not resolved.is_dir():
        return False
    return True


def fetch_all(config_path, outdir):
    if not _safe_outdir(outdir):
        raise ValueError("unsafe outdir")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if not isinstance(config, dict) or set(config.keys()) != set(SCHEMA.keys()):
        raise ValueError("config keys mismatch")
    for k in SCHEMA:
        v = config.get(k)
        if not isinstance(v, str) or not v or not _valid_url(v):
            raise ValueError("invalid url for %s" % k)
    data_dir = (ROOT / "data").resolve()
    tmp = Path(tempfile.mkdtemp(prefix="fetch_", dir=str(data_dir)))
    backup = None
    success = False
    try:
        for k in SCHEMA:
            text = fetch_csv(config[k])
            with open(tmp / (k + ".csv"), "w", encoding="utf-8", newline="") as f:
                f.write(text)
        validate(load_tables(tmp))
        out = Path(outdir).resolve()
        if out.exists():
            backup = Path(tempfile.mkdtemp(prefix="bak_", dir=str(data_dir)))
            backup.rmdir()
            os.replace(str(out), str(backup))
        try:
            os.replace(str(tmp), str(out))
        except Exception:
            if backup is not None and backup.exists() and not out.exists():
                os.replace(str(backup), str(out))
                backup = None
            raise
        success = True
        print("\t".join(["ok"] + [k for k in SCHEMA]))
    finally:
        if tmp.exists():
            shutil.rmtree(str(tmp), ignore_errors=True)
        if success and backup is not None and backup.exists():
            shutil.rmtree(str(backup), ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "sheets.json"))
    ap.add_argument("--output", default=str(ROOT / "data" / "live"))
    args = ap.parse_args(argv)
    try:
        fetch_all(args.config, args.output)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
