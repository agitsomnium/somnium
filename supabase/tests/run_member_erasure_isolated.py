"""Apply migrations 1-8, then the unapplied erasure draft, in a throwaway local PostgreSQL 17 cluster and run the regressions:
 1 erase + ledger, 2 rollback refused / clean / re-apply, 3 rollback refused for a member with no audit rows of their own,
 4 restoring a pre-erasure backup does not bring the erased member back once the ledger is applied.
Mock auth.users/auth.uid only; no network, no hosted project. Usage: python3 run_member_erasure_isolated.py [--log FILE]"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

PG = Path('/opt/homebrew/opt/postgresql@17/bin')
SUPABASE = Path(__file__).resolve().parents[1]
ROLES = "create role anon;create role authenticated;"
BOOTSTRAP = """
create schema auth;create table auth.users(id uuid primary key,email text,email_confirmed_at timestamptz);
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
grant usage on schema auth to authenticated;grant execute on function auth.uid() to authenticated;
create schema storage;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated;grant select,insert on storage.objects to authenticated;
create function storage.allow_only_operation(op text) returns boolean language sql stable as $$select current_setting('storage.operation',true)=op$$;
create function storage.allow_any_operation(ops text[]) returns boolean language sql stable as $$select current_setting('storage.operation',true)=any(ops)$$;
"""


SEED_SEMINAR = """insert into classroom_private.lessons(title,series_title,position,era,published,provider,video_id)
select '합성 세미나 '||g,'현대 자본주의 이해하기',g,'current',true,'youtube',repeat(chr(96+g),11) from generate_series(1,6) g;"""


def run(cmd, **kw):
    env = {**os.environ, 'LC_ALL': 'en_US.UTF-8'}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)
    if result.returncode:
        sys.exit(f'FAILED {cmd[-1]}\n{result.stderr}')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='somnium-pg-'))
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = str(probe.getsockname()[1])
    data = root / 'data'
    out = []
    env = {**os.environ, 'LC_ALL': 'en_US.UTF-8'}
    ok = False
    try:
        run([PG / 'initdb', '-D', str(data), '-U', 'postgres', '--locale=en_US.UTF-8', '-E', 'UTF8'])
        start = [PG / 'pg_ctl', '-D', str(data), '-o', f"-c listen_addresses=127.0.0.1 -p {port} -c unix_socket_directories=''", '-w', 'start', '-l', str(root / 'log')]
        started = subprocess.run(start, capture_output=True, text=True, env=env)
        if started.returncode:
            server_log = (root / 'log').read_text(errors='replace') if (root / 'log').exists() else '(server log file was not created)'
            sys.exit(f'FAILED pg_ctl start\n{started.stderr}\n--- server log ---\n{server_log}')

        def conn(db):
            return [PG / 'psql', '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', db, '-v', 'ON_ERROR_STOP=1', '-q']

        def scalar(db, sql):
            return run(conn(db) + ['-At', '-c', sql]).stdout.strip()

        def prepare(db, draft=True):
            if db != 'postgres':
                run(conn('postgres') + ['-c', f'create database {db}'])
            run(conn(db), input=BOOTSTRAP)
            for migration in sorted((SUPABASE / 'migrations').glob('*.sql')):
                if 'series_passes' in migration.name:
                    run(conn(db), input=SEED_SEMINAR)
                run(conn(db) + ['-f', str(migration)])
            run(conn(db) + ['-f', str(SUPABASE / 'proposed/20261101_minimal_profile_DRAFT.sql')])
            if draft:
                run(conn(db) + ['-f', str(SUPABASE / 'proposed/20261102_member_erasure_DRAFT.sql')])

        def as_admin_erase(db, admin, target):
            run(conn(db), input=f"begin; set local role authenticated; select set_config('request.jwt.claim.sub','{admin}',true); select public.somnium_erase_member('{target}'); commit;")

        rb = SUPABASE / 'proposed/20261102_member_erasure_ROLLBACK_DRAFT.sql'
        run(conn('postgres'), input=ROLES)

        # 1-2: main regression, then rollback behaviour
        run(conn('postgres'), input=BOOTSTRAP)
        for migration in sorted((SUPABASE / 'migrations').glob('*.sql')):
            if 'series_passes' in migration.name:
                run(conn('postgres'), input=SEED_SEMINAR)
            run(conn('postgres') + ['-f', str(migration)])
            out.append(f'applied {migration.name}')
        run(conn('postgres') + ['-f', str(SUPABASE / 'proposed/20261101_minimal_profile_DRAFT.sql')])
        result = subprocess.run(conn('postgres')[:-1] + ['-f', str(SUPABASE / 'tests/member-erasure.sql')], capture_output=True, text=True, cwd=SUPABASE / 'tests', env=env)
        out += [result.stdout, result.stderr]
        ok = result.returncode == 0 and 'MEMBER ERASURE PASS' in result.stdout
        if ok:
            refused = subprocess.run(conn('postgres') + ['-f', str(rb)], capture_output=True, text=True, env=env)
            ok = refused.returncode != 0 and 'rollback refused' in refused.stderr
            out.append('rollback refused while an erasure was executed: ' + ('PASS' if ok else 'FAIL ' + refused.stderr))
        if ok:
            before = scalar('postgres', "select (select count(*) from classroom_private.profiles)||'/'||(select count(*) from classroom_private.supporters)||'/'||(select count(*) from classroom_private.series_entitlements)||'/'||(select count(*) from auth.users)")
            run(conn('postgres') + ['-c', "delete from classroom_private.audit where actor is null or action='member_erased'; delete from classroom_private.erasure_ledger"])  # simulate: no member was erased
            run(conn('postgres') + ['-f', str(rb)])
            state = scalar('postgres', "select (select count(*) from pg_proc where proname in ('erase_member','erasure_ledger_pending','apply_erasure_ledger','import_erasure_ledger','export_erasure_ledger','erasure_hash'))||','||(select count(*) from pg_class where relname='erasure_ledger')||','||(select is_nullable from information_schema.columns where table_schema='classroom_private' and table_name='audit' and column_name='actor')||','||(select confdeltype::text from pg_constraint where conname='audit_actor_fkey')||','||(select (select count(*) from classroom_private.profiles)||'/'||(select count(*) from classroom_private.supporters)||'/'||(select count(*) from classroom_private.series_entitlements)||'/'||(select count(*) from auth.users))")
            ok = state == f'0,0,NO,a,{before}'
            out.append(f'rollback clean: state={state} expected=0,0,NO,a,{before}: ' + ('PASS' if ok else 'FAIL'))
        if ok:
            run(conn('postgres') + ['-f', str(SUPABASE / 'proposed/20261102_member_erasure_DRAFT.sql')])
            out.append('re-apply after rollback: PASS')

        # 3: member without any audit rows of their own
        if ok:
            prepare('noaudit')
            run(conn('noaudit') + ['-f', str(SUPABASE / 'tests/member-erasure-noaudit-seed.sql')])
            as_admin_erase('noaudit', '60000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000002')
            nulls = scalar('noaudit', "select count(*) from classroom_private.audit where actor is null")
            refused = subprocess.run(conn('noaudit') + ['-f', str(rb)], capture_output=True, text=True, env=env)
            still = scalar('noaudit', "select count(*) from pg_proc where proname='erase_member'")
            ok = nulls == '0' and refused.returncode != 0 and 'rollback refused' in refused.stderr and still == '1'
            out.append(f'rollback refused for a member with no audit rows of their own (audit rows with null actor={nulls}, so the old guard alone would have passed): ' + ('PASS' if ok else 'FAIL ' + refused.stderr))

        # 4: backup -> e-mail change -> erase -> restore the OLD backup -> apply the ledger (through the tool, with failure cases)
        if ok:
            TOOL = [sys.executable, str(SUPABASE / 'ops/erasure_ledger.py')]
            url = lambda db: f'postgresql://postgres@127.0.0.1:{port}/{db}'
            tool = lambda db, *a: subprocess.run(TOOL + ['--psql', url(db), *a], capture_output=True, text=True, env=env)
            prepare('restore_src')
            run(conn('restore_src') + ['-f', str(SUPABASE / 'tests/member-erasure-restore-seed.sql')])
            M = '40000000-0000-0000-0000-000000000002'
            dump = root / 'pre-erasure.sql'  # the "backup": taken before the e-mail change and before the erasure
            run([PG / 'pg_dump', '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', 'restore_src', '-f', str(dump)])
            run(conn('restore_src'), input=f"update auth.users set email='changed-after-backup@example.test' where id='{M}'; insert into classroom_private.audit(actor,action,target) values('40000000-0000-0000-0000-000000000001','director_updated','changed-after-backup@example.test');")
            as_admin_erase('restore_src', '40000000-0000-0000-0000-000000000001', M)
            outd, stored = root / 'ledger-out', root / 'ledger-store'
            ex = tool('restore_src', 'export', '--out-dir', str(outd), '--store-dir', str(stored))
            files = sorted(stored.glob('erasure-ledger-*.json'))
            exported = ex.returncode == 0 and ex.stdout.startswith('OK export') and len(files) == 1 and (outd / files[0].name).read_bytes() == files[0].read_bytes()
            out.append('tool export/store/re-read: ' + ('PASS ' + ex.stdout.strip() if exported else 'FAIL ' + ex.stdout + ex.stderr))
            ledger = files[0] if files else None
            text = ledger.read_text(encoding='utf-8') if ledger else ''
            secrets = ('erase-me', 'changed-after-backup', M, '복원 삭제', '01012345678', '1990-02-03', '@')
            clean = bool(text) and not any(x in text for x in secrets)
            out.append(f'ledger file holds no plaintext (old e-mail, new e-mail, id, name, phone, birth, "@"): {"PASS" if clean else "FAIL"}')
            ok = exported and clean
        if ok:
            ver = tool('restore_src', 'verify', '--file', str(ledger))
            ok = ver.returncode == 0 and ver.stdout.startswith('OK verify')
            out.append('tool verify against live database: ' + ('PASS' if ok else 'FAIL ' + ver.stdout))
        if ok:  # failure paths must fail, not report done
            doc = json.loads(text)
            def variant(name, mutate):
                d = json.loads(text); mutate(d)
                f = root / name; f.write_text(json.dumps(d), encoding='utf-8'); return f
            def refit(d):  # make the file self-consistent so only the database comparison can catch it
                d['count'] = len(d['entries']); d['entries_sha256'] = hashlib.sha256(json.dumps(d['entries'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            cases = {
                'edited hash (fingerprint)': ('verify', variant('t1.json', lambda d: d['entries'][0].__setitem__('id_hash', 'a' * 64))),
                'entry removed but file re-fingerprinted (database comparison)': ('verify', variant('t2.json', lambda d: (d['entries'].clear(), refit(d)))),
                'e-mail text inside a hash field': ('verify', variant('t3.json', lambda d: (d['entries'][0].__setitem__('email_hash', 'x@example.test'), refit(d)))),
                'missing file': ('verify', root / 'nope.json'),
                'apply with a damaged file': ('apply', variant('t5.json', lambda d: d.__setitem__('count', 99))),
            }
            bad = []
            for label, (cmd, f) in cases.items():
                r = tool('restore_src', cmd, '--file', str(f))
                if r.returncode != 1 or 'FAILED' not in r.stdout or 'OK' in r.stdout.split('FAILED')[0]:
                    bad.append(label)
            same = tool('restore_src', 'export', '--out-dir', str(outd), '--store-dir', str(outd))
            if same.returncode != 1 or 'FAILED' not in same.stdout:
                bad.append('store dir equals out dir')
            blocker = root / 'a-file'; blocker.write_text('x')
            blocked = tool('restore_src', 'export', '--out-dir', str(root / 'o2'), '--store-dir', str(blocker / 'sub'))
            if blocked.returncode == 0 or 'OK' in blocked.stdout:
                bad.append('unwritable store location')
            # stale file: a second erasure after the export must make verify fail
            run(conn('restore_src'), input="insert into auth.users(id,email) values('40000000-0000-0000-0000-000000000009','later@example.test'); insert into classroom_private.profiles(id,name,consent_version) values('40000000-0000-0000-0000-000000000009','나중 회원','v2');")
            as_admin_erase('restore_src', '40000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000009')
            stale = tool('restore_src', 'verify', '--file', str(ledger))
            if stale.returncode != 1 or 'FAILED' not in stale.stdout:
                bad.append('stale file after a later erasure')
            ok = not bad
            out.append('tool failure paths all exit 1 with FAILED: ' + ('PASS (%d cases)' % (len(cases) + 3) if ok else 'FAIL ' + ', '.join(bad)))
        if ok:
            fresh = tool('restore_src', 'export', '--out-dir', str(root / 'o3'), '--store-dir', str(root / 's3'))  # now includes both erasures
            ledger = sorted((root / 's3').glob('erasure-ledger-*.json'))[0]
            run(conn('postgres') + ['-c', 'create database restore_dst'])
            run(conn('restore_dst') + ['-f', str(dump)])
            gone = f"select (select count(*) from auth.users where id='{M}')||'/'||(select count(*) from classroom_private.profiles where id='{M}')||'/'||(select count(*) from classroom_private.supporters where user_id='{M}')||'/'||(select count(*) from classroom_private.series_entitlements where user_id='{M}')||'/'||(select count(*) from classroom_private.audit where target in ('{M}','erase-me@example.test','changed-after-backup@example.test'))"
            resurrected = scalar('restore_dst', gone)
            traces = lambda: subprocess.run([PG / 'pg_dump', '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', 'restore_dst', '--data-only'], capture_output=True, text=True).stdout
            before_traces = sum(traces().count(x) for x in ('erase-me', '복원 삭제', '01012345678', M))
            ap = tool('restore_dst', 'apply', '--file', str(ledger))
            after = scalar('restore_dst', gone)
            dumped = traces()
            left = {x: dumped.count(x) for x in ('erase-me', 'changed-after-backup', '복원 삭제', '01012345678', '1990-02-03', M)}
            again = tool('restore_dst', 'apply', '--file', str(ledger))
            keep = scalar('restore_dst', "select (select count(*) from auth.users)||'/'||(select count(*) from classroom_private.profiles where id='40000000-0000-0000-0000-000000000003')||'/'||(select count(*) from classroom_private.series_entitlements where user_id='40000000-0000-0000-0000-000000000003')||'/'||(select count(*) from classroom_private.admins)||'/'||(select count(*) from classroom_private.audit where target='40000000-0000-0000-0000-000000000003' or actor='40000000-0000-0000-0000-000000000003')")
            ok = (fresh.returncode == 0 and resurrected == '1/1/1/1/3' and before_traces > 0 and ap.returncode == 0 and ap.stdout.startswith('OK apply')
                  and after == '0/0/0/0/0' and not any(left.values()) and again.returncode == 0 and keep == '2/1/1/1/1')
            out.append(f'restore of the OLD backup without the ledger resurrects the member (user/profile/request/entitlement/audit-with-old-e-mail-or-id={resurrected}, plaintext traces in a data dump={before_traces}): ' + ('expected' if resurrected == '1/1/1/1/3' and before_traces > 0 else 'UNEXPECTED'))
            out.append(f'tool apply: {ap.stdout.strip() or ap.stderr.strip()}')
            out.append(f'after apply: rows {after}; plaintext traces left in a full data dump (old e-mail, new e-mail, name, phone, birth, id) = {left}; second apply exit {again.returncode}; other member + admin kept (users/profile/entitlement/admins/audit rows)={keep}: ' + ('PASS' if ok else 'FAIL'))
        out.append('RESULT: ' + ('PASS' if ok else 'FAIL'))
    finally:
        subprocess.run([PG / 'pg_ctl', '-D', str(data), '-m', 'immediate', 'stop'], capture_output=True)
        shutil.rmtree(root, ignore_errors=True)
    text = '\n'.join(out)
    print(text)
    if args.log:
        args.log.write_text(text, encoding='utf-8')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
