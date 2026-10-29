"""Copy synthetic trial DB/media to a NEW directory; verify hashes on restore.

Not a production backup service. Never copies sessions or authentication codes.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('새 디렉터리만 사용할 수 있습니다.')
    if not (source / 'trial.sqlite3').is_file():
        raise ValueError('시험 DB 없음')
    manifest_path = source / 'backup-manifest.json'
    if manifest_path.exists():
        for name, value in json.loads(manifest_path.read_text()).items():
            if Path(name).name != name or sha(source / name) != value:
                raise ValueError('백업 지문 불일치')
    destination.mkdir(mode=0o700, parents=True)
    original = sqlite3.connect(f'file:{source / "trial.sqlite3"}?mode=ro', uri=True)
    copied = sqlite3.connect(destination / 'trial.sqlite3')
    try:
        original.backup(copied)
        copied.execute('delete from sessions')
        copied.execute('delete from otps')
        copied.commit()
        assert copied.execute('pragma integrity_check').fetchone()[0] == 'ok'
        rows = copied.execute('select video,material from lessons').fetchall()
    finally:
        original.close()
        copied.close()
    for row in rows:
        for name in row:
            if Path(name).name != name:
                raise ValueError('자료 경로 확인 필요')
            shutil.copyfile(source / name, destination / name)
    manifest = {p.name: sha(p) for p in destination.iterdir() if p.is_file()}
    (destination / 'backup-manifest.json').write_text(json.dumps(manifest, indent=2))
    return {'files': len(manifest), 'verified': True, 'authentication_removed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.source, args.destination)))
