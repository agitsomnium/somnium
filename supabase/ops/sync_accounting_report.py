"""AI-operated, idempotent sync of an explicitly reviewed member report. No scheduler.
Preview is local only. Credentials stay inside this process; raw ledgers are never selected.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from html import unescape
from pathlib import Path

REF = 'jdfrottxrdhglxtqvtyx'
BUCKET = 'somnium-accounting'
ADMIN = 'agit.somnium@gmail.com'
MAX_SIZE = 25 * 1024 * 1024


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def prepare(manifest_path):
    p = Path(manifest_path).resolve()
    m = json.loads(p.read_text())
    if set(m) != {'file', 'title', 'period', 'sha256', 'member_safe', 'publish'}:
        raise ValueError('manifest fields invalid')
    if m['member_safe'] is not True or type(m['publish']) is not bool:
        raise ValueError('explicit member-safe review and boolean publish required')
    for field, limit in [('title', 160), ('period', 80)]:
        if not isinstance(m[field], str) or len(m[field]) > limit:
            raise ValueError('invalid ' + field)
    if not m['title'].strip():
        raise ValueError('title required')
    f = Path(m['file'])
    f = (p.parent / f).resolve() if not f.is_absolute() else f.resolve()
    if f.suffix.lower() not in ('.pdf', '.html') or len(f.name) > 220 or '\\' in f.name:
        raise ValueError('PDF filename required')
    if not 0 < f.stat().st_size <= MAX_SIZE:
        raise ValueError('PDF size out of range')
    data = f.read_bytes()
    if f.suffix.lower() == '.pdf' and not data.startswith(b'%PDF-'):
        raise ValueError('PDF header missing')
    if f.suffix.lower() == '.html':
        body = unescape(data.decode('utf-8'))
        if 'somnium-finance-paper/1' not in body or "default-src 'none'" not in body or "connect-src 'none'" not in body:
            raise ValueError('self-contained sandbox report required')
    digest = hashlib.sha256(data).hexdigest()
    if digest != m['sha256']:
        raise ValueError('reviewed PDF fingerprint mismatch')
    # Same bytes map to the same immutable object; reruns do not add reports.
    name = str(uuid.uuid5(uuid.NAMESPACE_URL, 'somnium-accounting:' + digest)) + f.suffix.lower()
    return m, f, data, name


class Backend:
    def query(self, sql):
        r = subprocess.run(['supabase', 'db', 'query', '--linked', '--project-ref', REF,
                            sql, '--output', 'json'], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parents[2])
        if r.returncode:
            raise RuntimeError('database command failed')
        try:
            return json.loads(r.stdout[r.stdout.index('{'):])['rows']
        except (ValueError, KeyError):
            raise RuntimeError('database response invalid') from None

    def key(self):
        r = subprocess.run(['supabase', 'projects', 'api-keys', '--project-ref', REF,
                            '-o', 'json'], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('credential retrieval failed')
        try:
            return next(k['api_key'] for k in json.loads(r.stdout)
                        if k.get('name') == 'service_role' or k.get('id') == 'service_role')
        except (ValueError, KeyError, StopIteration):
            raise RuntimeError('credential unavailable') from None

    def object(self, name, data=None):
        key = self.key()
        req = urllib.request.Request(
            f'https://{REF}.supabase.co/storage/v1/object/{BUCKET}/{name}', data=data,
            method='POST' if data is not None else 'GET',
            headers={'Authorization': 'Bearer ' + key, 'apikey': key,
                     'Content-Type': 'text/html' if name.endswith('.html') else 'application/pdf', 'x-upsert': 'false'})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            # Only explicit object conflicts are recoverable, after full readback.
            if data is not None and exc.code in (400, 409):
                body = exc.read()
                if b'Duplicate' in body or b'already exists' in body:
                    return None
            raise RuntimeError('storage request failed (HTTP ' + str(exc.code) + ')') from None

    def find(self, name):
        return self.query('select id,title,period,filename,enabled from '
                          'classroom_private.accounting_reports where storage_path=' + literal(name))

    def save(self, m, f, name):
        enabled = 'true' if m['publish'] else 'false'
        # Existing institution administrator is required; never create an admin.
        return self.query("begin; do $$ begin if not exists(select 1 from auth.users u "
            "join classroom_private.admins a on a.user_id=u.id where lower(u.email)="
            + literal(ADMIN) + " and a.enabled and u.email_confirmed_at is not null) then "
            "raise exception 'institution admin missing'; end if; end $$; "
            "select set_config('request.jwt.claim.sub',(select id::text from auth.users where lower(email)="
            + literal(ADMIN) + "),true); select classroom_private.save_report("
            + ','.join([literal(m['title'].strip()), literal(m['period'].strip()),
                        literal(f.name), literal(name), enabled]) + "); commit;")


def sync(m, f, data, name, backend):
    rows = backend.find(name)
    if rows:
        row = rows[0]
        expected = {'title': m['title'].strip(), 'period': m['period'].strip(),
                    'filename': f.name, 'enabled': m['publish']}
        if any(row[k] != v for k, v in expected.items()):
            raise ValueError('existing report differs; do not overwrite or republish automatically')
    else:
        backend.object(name, data)
    if backend.object(name) != data:
        raise ValueError('stored PDF readback mismatch')
    if not rows:
        backend.save(m, f, name)
        rows = backend.find(name)
        expected = {'title': m['title'].strip(), 'period': m['period'].strip(),
                    'filename': f.name, 'enabled': m['publish']}
        if len(rows) != 1 or any(rows[0][k] != v for k, v in expected.items()):
            raise ValueError('saved report verification failed')
    return rows[0]['id']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        m, f, data, name = prepare(args.manifest)
        if not args.apply:
            print(json.dumps({'mode': 'preview', 'network': False, 'bytes': len(data),
                              'sha256': m['sha256'], 'publish': m['publish'],
                              'storage_path': name}, ensure_ascii=False))
        else:
            report_id = sync(m, f, data, name, Backend())
            print('OK sync report=' + report_id)
        return 0
    except Exception as exc:
        # Never print unexpected library/CLI errors that could contain credentials.
        message = str(exc) if type(exc) in (ValueError, RuntimeError) else type(exc).__name__
        print('FAILED sync: ' + message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
