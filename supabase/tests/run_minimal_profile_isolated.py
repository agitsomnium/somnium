"""Apply migrations 1-8, then the unapplied draft, in a throwaway local PostgreSQL 17 cluster and run the regression.
Mock auth.users/auth.uid only; no network, no hosted project. Usage: python3 run_minimal_profile_isolated.py [--log FILE]"""
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
BOOTSTRAP = """create role anon;create role authenticated;
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
    try:
        run([PG / 'initdb', '-D', str(data), '-U', 'postgres', '--locale=en_US.UTF-8', '-E', 'UTF8'])
        run([PG / 'pg_ctl', '-D', str(data), '-o', f"-c listen_addresses=127.0.0.1 -p {port} -c unix_socket_directories=''", '-w', 'start', '-l', str(root / 'log')])
        psql = [PG / 'psql', '-h', '127.0.0.1', '-p', port, '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q']
        run(psql, input=BOOTSTRAP)
        for migration in sorted((SUPABASE / 'migrations').glob('*.sql')):
            if 'series_passes' in migration.name:
                run(psql, input=SEED_SEMINAR)
            run(psql + ['-f', str(migration)])
            out.append(f'applied {migration.name}')
        result = subprocess.run(psql[:-1] + ['-f', str(SUPABASE / 'tests/minimal-profile.sql')], capture_output=True, text=True, cwd=SUPABASE / 'tests', env={**os.environ, 'LC_ALL': 'en_US.UTF-8'})
        out += [result.stdout, result.stderr]
        ok = result.returncode == 0 and 'MINIMAL PROFILE PASS' in result.stdout
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
