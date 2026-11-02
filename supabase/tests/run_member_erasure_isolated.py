"""Apply migrations 1-8, then the unapplied erasure draft, in a throwaway local PostgreSQL 17 cluster and run the regressions:
 1 erase + ledger, 2 rollback refused / clean / re-apply, 3 rollback refused for a member with no audit rows of their own,
 4 restoring a pre-erasure backup does not bring the erased member back once the ledger is applied.
Mock auth.users/auth.uid only; no network, no hosted project. Usage: python3 run_member_erasure_isolated.py [--log FILE]"""
import argparse
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
            state = scalar('postgres', "select (select count(*) from pg_proc where proname in ('erase_member','apply_erasure_ledger','import_erasure_ledger','export_erasure_ledger','erasure_hash'))||','||(select count(*) from pg_class where relname='erasure_ledger')||','||(select is_nullable from information_schema.columns where table_schema='classroom_private' and table_name='audit' and column_name='actor')||','||(select confdeltype::text from pg_constraint where conname='audit_actor_fkey')||','||(select (select count(*) from classroom_private.profiles)||'/'||(select count(*) from classroom_private.supporters)||'/'||(select count(*) from classroom_private.series_entitlements)||'/'||(select count(*) from auth.users))")
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

        # 4: restore of a pre-erasure backup must not resurrect the erased member
        if ok:
            prepare('restore_src')
            run(conn('restore_src') + ['-f', str(SUPABASE / 'tests/member-erasure-restore-seed.sql')])
            dump = root / 'pre-erasure.sql'  # the "backup": taken before the erasure
            run([PG / 'pg_dump', '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', 'restore_src', '-f', str(dump)])
            as_admin_erase('restore_src', '40000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000002')
            ledger = root / 'ledger.json'  # kept outside the backup
            ledger.write_text(scalar('restore_src', 'select classroom_private.export_erasure_ledger()'), encoding='utf-8')
            text = ledger.read_text(encoding='utf-8')
            clean = not any(x in text for x in ('erase-me', '40000000-0000-0000-0000-000000000002', '복원 삭제', '01012345678', '1990-02-03'))
            run(conn('postgres') + ['-c', 'create database restore_dst'])
            run(conn('restore_dst') + ['-f', str(dump)])
            gone = "select (select count(*) from auth.users where id='40000000-0000-0000-0000-000000000002')||'/'||(select count(*) from classroom_private.profiles where id='40000000-0000-0000-0000-000000000002')||'/'||(select count(*) from classroom_private.supporters where user_id='40000000-0000-0000-0000-000000000002')||'/'||(select count(*) from classroom_private.series_entitlements where user_id='40000000-0000-0000-0000-000000000002')||'/'||(select count(*) from classroom_private.audit where target in ('40000000-0000-0000-0000-000000000002','erase-me@example.test'))"
            resurrected = scalar('restore_dst', gone)
            run(conn('restore_dst'), input=f"select classroom_private.import_erasure_ledger($j${text}$j$::jsonb);")
            applied = scalar('restore_dst', 'select classroom_private.apply_erasure_ledger()')
            after = scalar('restore_dst', gone)
            again = scalar('restore_dst', 'select classroom_private.apply_erasure_ledger()')
            keep = scalar('restore_dst', "select (select count(*) from auth.users)||'/'||(select count(*) from classroom_private.profiles where id='40000000-0000-0000-0000-000000000003')||'/'||(select count(*) from classroom_private.series_entitlements where user_id='40000000-0000-0000-0000-000000000003')||'/'||(select count(*) from classroom_private.admins)")
            ok = clean and resurrected == '1/1/1/1/3' and applied == '1' and after == '0/0/0/0/0' and again == '0' and keep == '2/1/1/1'
            out.append(f'restore without ledger resurrects the member (user/profile/request/entitlement/audit={resurrected}): ' + ('expected' if resurrected == '1/1/1/1/3' else 'UNEXPECTED'))
            out.append(f'ledger file holds no plaintext identity: {"PASS" if clean else "FAIL"}')
            out.append(f'after import+apply: re-erased={applied}, remaining traces={after}, second apply={again}, other members and admin kept={keep}: ' + ('PASS' if ok else 'FAIL'))
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
