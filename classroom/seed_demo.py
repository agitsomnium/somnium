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
        fixtures = [
            ('demo-archive','이전 강의 아카이브 · 시험 영상','','archive'),
            ('demo-capitalism-1','현대 자본주의 이해하기 · 시험 1강','capitalism-season1','current'),
            ('demo-capitalism-2','현대 자본주의 이해하기 · 시험 2강','capitalism-season1','current'),
            ('demo-2027','2027 신규 강좌 · 판매 준비 시험','new-2027','future'),
        ]
        fixtures += [(f'demo-capitalism-{i}',f'현대 자본주의 이해하기 · 시험 {i}강','capitalism-season1','current') for i in range(3,7)]
        for lid,title,series,era in fixtures:
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
            number=int(lid.rsplit('-',1)[-1]) if series=='capitalism-season1' else 1
            db.execute("update lessons set description=case when description='' then ? else description end, position=?,series_title=case when series_title='' then ? else series_title end where id=?",
                ('시험 영상과 자료로 강의실 이용 흐름을 살펴보는 가상 강의입니다. 실제 강의 내용은 포함하지 않았습니다.',number,'현대 자본주의 이해하기 · 시즌 1' if series=='capitalism-season1' else ('2027 신규 강좌' if series else ''),lid))
    return {'synthetic_members':3,'test_lessons':8,'real_data':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--video',type=Path,required=True)
    args=parser.parse_args()
    print(seed(args.state,args.video))
