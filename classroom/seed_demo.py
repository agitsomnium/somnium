"""Create synthetic review fixtures outside the public build. No real member data."""
import argparse
import hashlib
import shutil
import time
from pathlib import Path
from server import Trial


def seed(folder, video):
    trial=Trial(folder)
    video=Path(video)
    if not video.is_file() or b'ftyp' not in video.read_bytes()[:32]:
        raise ValueError('실제 시험용 MP4가 필요합니다.')
    with trial.connect() as db:
        for email,name,audience,status in (
            ('supporter@example.test','가상 후원회원','supporter','approved'),
            ('buyer@example.test','가상 강좌 구매자','purchase','approved'),
            ('pending@example.test','가상 승인 대기자','supporter','pending'),
        ):
            db.execute('''insert or ignore into members values (?,?,?,?,?,?,1,?,'member',?)''',
                       (email,name,'1990-01-01','01000000000','trial-2026-10-29',time.time(),status,audience))
        db.execute("insert or ignore into supporters(email,qualified,checked_at,checked_by,review_state) values ('supporter@example.test',1,?,'synthetic-demo','qualified')",(time.time(),))
        for lid,title,series,era in (
            ('demo-archive','이전 강의 아카이브 · 시험 영상','','archive'),
            ('demo-capitalism-1','현대 자본주의 이해하기 · 시험 1강','capitalism-season1','current'),
            ('demo-capitalism-2','현대 자본주의 이해하기 · 시험 2강','capitalism-season1','current'),
            ('demo-2027','2027 신규 강좌 · 판매 준비 시험','new-2027','future'),
        ):
            vname,mname=lid+'.mp4',lid+'.txt'
            target=trial.folder/vname
            if target.exists() and hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(video.read_bytes()).digest():
                raise ValueError('기존 시험 파일이 다릅니다. 덮어쓰지 않습니다.')
            if not target.exists():
                shutil.copyfile(video,target)
            material=trial.folder/mname
            if not material.exists():
                material.write_text('가상 회원용 시험 자료입니다. 실제 강의 원문이 아닙니다.\nPRIVATE_DRAFT_CANARY_20261030')
            db.execute('''insert or ignore into lessons(id,title,audience,published,video,material,series_id,era,supporter_access,purchasable)
              values (?,?,'supporter',1,?,?,?,?,?,?)''',
              (lid,title,vname,mname,series,era,'included',int(era!='archive')))
    return {'synthetic_members':3,'test_lessons':4,'real_data':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--video',type=Path,required=True)
    args=parser.parse_args()
    print(seed(args.state,args.video))
