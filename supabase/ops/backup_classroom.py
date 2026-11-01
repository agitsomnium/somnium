"""Logical backup of the somnium-classroom project: DB rows (classroom_private, auth users/identities, storage metadata) + Storage files.
Writes plaintext only into a 0700 working dir; caller encrypts and deletes. Service key is read inside this process and never printed."""
import hashlib, json, os, subprocess, sys, urllib.request
from pathlib import Path

REF = 'jdfrottxrdhglxtqvtyx'
OUT = Path(sys.argv[1])
if OUT.exists():
    sys.exit('Output directory already exists; choose a new private backup directory')
OUT.mkdir(mode=0o700, parents=True)
# Query the explicit project; no missing handoff-local linked directory.
os.chmod(OUT,0o700)

def query(sql):
    r = subprocess.run(['supabase', 'db', 'query', '--linked', '--project-ref', REF, sql], capture_output=True, text=True)
    t = r.stdout
    if '{' not in t: sys.exit('query failed: ' + r.stderr[-300:])
    return json.loads(t[t.index('{'):])['rows']

tables = [r['table_name'] for r in query("select table_name from information_schema.tables where table_schema='classroom_private' and table_type='BASE TABLE' order by 1")]
manifest = {'project': REF, 'tables': {}, 'files': []}
def dump(schema, table, cols='*'):
    rows = query(f"select {cols} from {schema}.{table}")
    (OUT / f'{schema}.{table}.json').write_text(json.dumps(rows, ensure_ascii=False))
    manifest['tables'][f'{schema}.{table}'] = len(rows)
for t in tables: dump('classroom_private', t)
dump('auth', 'users', "id,instance_id,aud,role,email,email_confirmed_at,phone,created_at,updated_at,raw_app_meta_data,raw_user_meta_data,is_sso_user,is_anonymous")
dump('auth', 'identities', "id,user_id,provider_id,identity_data,provider,created_at,updated_at")
dump('storage', 'buckets')
dump('storage', 'objects', "id,bucket_id,name,owner,created_at,updated_at,metadata,version")

keys = json.loads(subprocess.run(['supabase', 'projects', 'api-keys', '--project-ref', REF, '-o', 'json'], capture_output=True, text=True).stdout)
service = next(k['api_key'] for k in keys if k.get('name') == 'service_role' or k.get('id') == 'service_role')
objs = json.loads((OUT / 'storage.objects.json').read_text())
(OUT / 'files').mkdir(exist_ok=True)
for o in objs:
    req = urllib.request.Request(f"https://{REF}.supabase.co/storage/v1/object/{o['bucket_id']}/{o['name']}", headers={'Authorization': 'Bearer ' + service, 'apikey': service})
    data = urllib.request.urlopen(req, timeout=120).read()
    rel = hashlib.sha256((o['bucket_id'] + '/' + o['name']).encode()).hexdigest()[:16]
    (OUT / 'files' / rel).write_bytes(data)
    manifest['files'].append({'bucket': o['bucket_id'], 'name': o['name'], 'stored_as': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
print('tables', len(manifest['tables']), 'rows', sum(manifest['tables'].values()), 'files', len(manifest['files']), 'bytes', sum(f['bytes'] for f in manifest['files']))
