"""Apply every migration to a throwaway local PostgreSQL cluster (mock auth/storage/net, no network, no hosted project)
and run the given regression files. Usage: python3 run_isolated.py tests/a.sql [tests/b.sql ...]
PostgreSQL binaries: $SOMNIUM_PG_BIN (default: Homebrew postgresql@17). Must not run as root."""
import os, shutil, socket, subprocess, sys, tempfile
from pathlib import Path

PG = Path(os.environ.get('SOMNIUM_PG_BIN', '/opt/homebrew/opt/postgresql@17/bin'))
SUPABASE = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
create role anon;create role authenticated;create role service_role;
create schema auth;create table auth.users(id uuid primary key,email text,email_confirmed_at timestamptz);
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
grant usage on schema auth to authenticated;grant execute on function auth.uid() to authenticated;
create schema storage;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,metadata jsonb);
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated;grant select,insert on storage.objects to authenticated;
create function storage.allow_only_operation(op text) returns boolean language sql stable as $$select current_setting('storage.operation',true)=op$$;
create function storage.allow_any_operation(ops text[]) returns boolean language sql stable as $$select current_setting('storage.operation',true)=any(ops)$$;
create schema extensions;create schema net;
create function net.http_post(url text,body jsonb default '{}',params jsonb default '{}',headers jsonb default '{}',timeout_milliseconds int default 5000) returns bigint language sql as $$select 1::bigint$$;
"""
SEED_SEMINAR = """insert into classroom_private.lessons(title,series_title,position,era,published,provider,video_id)
select '합성 세미나 '||g,'현대 자본주의 이해하기',g,'current',true,'youtube',repeat(chr(96+g),11) from generate_series(1,6) g;"""


def main():
    tests = [Path(a).resolve() for a in sys.argv[1:]]
    root = Path(tempfile.mkdtemp(prefix='somnium-pg-')); data = root / 'data'
    env = {**os.environ, 'LC_ALL': 'en_US.UTF-8'}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = str(probe.getsockname()[1])
    psql = [str(PG / 'psql'), '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q']
    failed = 0
    try:
        subprocess.run([str(PG / 'initdb'), '-D', str(data), '-U', 'postgres', '--locale=en_US.UTF-8', '-E', 'UTF8'], check=True, capture_output=True, env=env)
        subprocess.run([str(PG / 'pg_ctl'), '-D', str(data), '-o', f"-c listen_addresses=127.0.0.1 -p {port} -c unix_socket_directories=''", '-w', 'start', '-l', str(root / 'log')], check=True, capture_output=True, env=env)
        def run(sql=None, file=None):
            r = subprocess.run(psql + (['-f', str(file)] if file else []), input=sql, capture_output=True, text=True, env=env, cwd=SUPABASE / 'tests')
            return r
        assert run(BOOTSTRAP).returncode == 0
        for migration in sorted((SUPABASE / 'migrations').glob('*.sql')):
            if 'series_passes' in migration.name: run(SEED_SEMINAR)
            if 'lecture_dates' in migration.name: run('update classroom_private.lessons set published=false')  # seed rows carry no date
            body = migration.read_text().replace('create extension if not exists pg_net with schema extensions;', '')
            r = run(body)
            if r.returncode: sys.exit('FAILED migration ' + migration.name + '\n' + r.stderr)
        # applied to the hosted project out of band on 2026-11-01; later functions read its columns
        r = run(file=SUPABASE / 'proposed/20261101_minimal_profile_DRAFT.sql')
        if r.returncode: sys.exit('FAILED minimal profile draft\n' + r.stderr)
        print('applied %d migrations' % len(list((SUPABASE / 'migrations').glob('*.sql'))))
        for test in tests:
            r = run(file=test); ok = r.returncode == 0 and 'PASS' in r.stdout
            failed += not ok
            print(('PASS ' if ok else 'FAIL ') + test.name + ('' if ok else '\n' + r.stdout[-600:] + r.stderr[-1500:]))
    finally:
        subprocess.run([str(PG / 'pg_ctl'), '-D', str(data), '-m', 'immediate', 'stop'], capture_output=True, env=env)
        shutil.rmtree(root, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == '__main__': main()
