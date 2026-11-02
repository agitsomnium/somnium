"""Erasure ledger tool: export -> store -> re-read, verify, and apply after a restore. Every step re-checks itself; any failure exits 1
and prints a line starting with FAILED. Do not report the work as done unless the last line starts with OK.

  export --out-dir DIR --store-dir DIR2   write the ledger from the database to DIR, copy to DIR2 (a different location, e.g. the institution
                                          Drive folder), re-read both files, and compare them with a fresh query of the database
  verify --file F                         check a stored ledger file and compare it with the live database (every database entry must be in the file with the same
                                          e-mail hash, erasure time and counts, not just the same id)
  apply  --file F                         after restoring a backup: import the file, run the re-erasure, and require 0 remaining members

Database access (pick one):  --psql URL   (e.g. postgresql://postgres@127.0.0.1:5432/db, used for isolated tests)
                             --ref REF    (hosted project through the authenticated `supabase db query --linked`)
The ledger holds only one-way hashes and counts. The tool refuses a file that contains an '@' or a UUID-shaped string.
It prints counts, never entries. Nothing here deletes data except `apply`, which only re-erases members already in the ledger."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

HEX64 = re.compile(r'^[0-9a-f]{64}$')
UUID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
KEYS = {'id_hash', 'email_hash', 'erased_at', 'removed'}


def fail(msg):
    print('FAILED: ' + msg + ' — do NOT report this as complete.')
    sys.exit(1)


class Db:
    def __init__(self, args):
        if bool(args.psql) == bool(args.ref):
            fail('give exactly one of --psql or --ref')
        self.args = args

    def value(self, sql):
        """Run `select <jsonb> as v` and return the decoded value."""
        if self.args.psql:
            r = subprocess.run(['psql', self.args.psql, '-At', '-v', 'ON_ERROR_STOP=1', '-c', sql], capture_output=True, text=True)
            if r.returncode:
                fail('database query failed: ' + r.stderr.strip()[-300:])
            return json.loads(r.stdout.strip().split('\n')[0])
        r = subprocess.run(['supabase', 'db', 'query', '--linked', '--project-ref', self.args.ref, sql], capture_output=True, text=True)
        t = r.stdout
        if '{' not in t:
            fail('database query failed: ' + r.stderr.strip()[-300:])
        rows = json.loads(t[t.index('{'):])['rows']
        if len(rows) != 1:
            fail('unexpected query result')
        v = rows[0]['v']
        return json.loads(v) if isinstance(v, str) else v


def canonical(entries):
    return json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def check_entries(entries):
    if not isinstance(entries, list):
        fail('ledger is not a list')
    seen = set()
    for e in entries:
        if not isinstance(e, dict) or not set(e) <= KEYS or not HEX64.match(str(e.get('id_hash', ''))):
            fail('ledger entry has an unexpected shape')
        if e.get('email_hash') is not None and not HEX64.match(str(e['email_hash'])):
            fail('ledger entry has a non-hash e-mail field')
        if e['id_hash'] in seen:
            fail('duplicate ledger entry')
        seen.add(e['id_hash'])
    text = canonical(entries)
    if '@' in text or UUID.search(text) or '$j$' in text:
        fail('ledger contains something that looks like plaintext identity')
    return seen


def read_file(path):
    path = Path(path)
    if not path.is_file():
        fail(f'file not found: {path.name}')
    raw = path.read_bytes()
    try:
        doc = json.loads(raw)
    except ValueError:
        fail(f'{path.name} is not valid JSON')
    if doc.get('version') != 1 or 'entries' not in doc:
        fail(f'{path.name} is not an erasure ledger file')
    ids = check_entries(doc['entries'])
    if doc.get('count') != len(doc['entries']) or doc.get('entries_sha256') != hashlib.sha256(canonical(doc['entries']).encode()).hexdigest():
        fail(f'{path.name} fails its own count/fingerprint (damaged or edited)')
    return doc, ids, hashlib.sha256(raw).hexdigest()


def differences(live, filed):
    """Compare whole entries by id_hash: e-mail hash, erasure time and removed counts must match, not only the ids.
    Returns (missing_from_file, changed_count)."""
    by_id = {e['id_hash']: e for e in filed}
    missing = [e for e in live if e['id_hash'] not in by_id]
    changed = [e for e in live if e['id_hash'] in by_id and canonical(by_id[e['id_hash']]) != canonical(e)]
    return len(missing), len(changed)


def live_ids(db):
    entries = db.value("select classroom_private.export_erasure_ledger() as v")
    return entries, check_entries(entries)


def cmd_export(args):
    db = Db(args)
    entries, ids = live_ids(db)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    doc = {'version': 1, 'exported_at': stamp, 'count': len(entries), 'entries': entries,
           'entries_sha256': hashlib.sha256(canonical(entries).encode()).hexdigest()}
    name = f'erasure-ledger-{stamp}.json'
    out_dir, store_dir = Path(args.out_dir), Path(args.store_dir)
    if out_dir.resolve() == store_dir.resolve():
        fail('--store-dir must be a different folder from --out-dir')
    for d in (out_dir, store_dir):
        d.mkdir(parents=True, exist_ok=True)
        if not os.access(d, os.W_OK):
            fail(f'folder is not writable: {d}')
    first, second = out_dir / name, store_dir / name
    if first.exists() or second.exists():
        fail('target file already exists')
    first.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    os.chmod(first, 0o600)
    shutil.copyfile(first, second)
    h1 = read_file(first)[2]
    _, ids2, h2 = read_file(second)
    if h1 != h2:
        fail('stored copy differs from the exported file')
    now, _ = live_ids(db)  # re-query after writing: nothing may have been erased or changed in between
    miss, chg = differences(now, read_file(second)[0]['entries'])
    if miss or chg:
        fail(f'the database differs from the stored file ({miss} entries missing, {chg} entries with different e-mail hash / erasure time / counts); export again')
    print(f'OK export: {len(entries)} entries, sha256 {h1[:16]}, written and re-read in {first.parent.name}/ and {second.parent.name}/ ({name})')


def cmd_verify(args):
    db = Db(args)
    doc, ids, h = read_file(args.file)
    now, now_ids = live_ids(db)
    miss, chg = differences(now, doc['entries'])
    if miss or chg:
        fail(f'{Path(args.file).name} does not match the database: {miss} entries missing, {chg} entries with different e-mail hash / erasure time / counts')
    print(f'OK verify: file has {len(ids)} entries (sha256 {h[:16]}), database has {len(now_ids)}, every database entry matches the file in full')


def cmd_apply(args):
    db = Db(args)
    doc, ids, h = read_file(args.file)
    payload = canonical(doc['entries'])
    db.value(f"select classroom_private.import_erasure_ledger($j${payload}$j$::jsonb) as v")
    now, _ = live_ids(db)
    miss, chg = differences(doc['entries'], now)  # every file entry must exist in the database with identical content
    if miss or chg:
        fail(f'after import the database ledger lacks {miss} file entries or holds {chg} with different content (a stale or conflicting ledger already exists); stop and check by hand')
    erased = db.value('select classroom_private.apply_erasure_ledger() as v')
    pending = db.value('select classroom_private.erasure_ledger_pending() as v')
    if pending != 0:
        fail(f'{pending} ledger members are still present after apply')
    again = db.value('select classroom_private.apply_erasure_ledger() as v')
    if again != 0:
        fail('a second apply still found members')
    print(f'OK apply: ledger {len(ids)} entries imported, {erased} restored members re-erased, 0 remaining, second run 0')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--psql')
    ap.add_argument('--ref')
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('--out-dir', required=True)
    e.add_argument('--store-dir', required=True)
    for n in ('verify', 'apply'):
        sub.add_parser(n).add_argument('--file', required=True)
    args = ap.parse_args()
    {'export': cmd_export, 'verify': cmd_verify, 'apply': cmd_apply}[args.cmd](args)


if __name__ == '__main__':
    main()
