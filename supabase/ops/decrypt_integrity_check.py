"""Backup DECRYPTION + INTEGRITY CHECK (not a restore test): decrypt an encrypted backup with a passphrase typed by the operator and verify it, without printing data.
It proves the institution holds a working passphrase and an uncorrupted file. It does NOT prove the data can be loaded into a running database;
that is covered separately by tests/run_member_erasure_isolated.py (restore into isolated PostgreSQL) and is not an independent Auth restore.
Usage: decrypt_integrity_check.py /path/to/backup.tar.gz.enc
The passphrase is read with getpass (or SOMNIUM_BACKUP_PASSPHRASE for automated tests of this script) and only piped to openssl.
Checks: decryption, archive integrity, manifest present, every Storage file's sha256 and size, table row counts vs manifest.
It restores nothing and writes nothing outside a temporary directory that is deleted at the end. Needs only python3 and openssl."""
import getpass, hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    enc = Path(sys.argv[1])
    if not enc.is_file():
        sys.exit('encrypted file not found')
    key = (os.environ.get('SOMNIUM_BACKUP_PASSPHRASE') or getpass.getpass('Backup passphrase (hidden): ')).encode() + b'\n'
    tmp = Path(tempfile.mkdtemp(prefix='somnium-check-'))
    os.chmod(tmp, 0o700)
    try:
        out = tmp / 'backup.tar.gz'
        r = subprocess.run(['/usr/bin/openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', '600000', '-in', str(enc), '-out', str(out), '-pass', 'stdin'], input=key, capture_output=True)
        if r.returncode or not out.exists() or out.stat().st_size == 0:
            sys.exit('CHECK FAIL: could not decrypt (wrong passphrase or damaged file)')
        with tarfile.open(out) as tar:
            tar.extractall(tmp, filter='data')
        root = tmp / 'backup'
        manifest = json.loads((root / 'manifest.json').read_text())
        problems = []
        rows = 0
        for name, count in manifest['tables'].items():
            data = json.loads((root / f'{name}.json').read_text())
            rows += len(data)
            if len(data) != count:
                problems.append(f'rows {name}: {len(data)} != {count}')
        size = 0
        for f in manifest['files']:
            blob = (root / 'files' / f['stored_as']).read_bytes()
            size += len(blob)
            if hashlib.sha256(blob).hexdigest() != f['sha256'] or len(blob) != f['bytes']:
                problems.append(f"file mismatch {f['stored_as']}")
        print(f"tables {len(manifest['tables'])} rows {rows} files {len(manifest['files'])} bytes {size}")
        if problems:
            sys.exit('CHECK FAIL: ' + '; '.join(problems))
        print('CHECK PASS (decryption + integrity only): decrypted, manifest and all files match. Nothing was restored; this is not a restore test.')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
