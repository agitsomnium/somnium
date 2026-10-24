"""data/sheet_seed/*.csv(내부 머리글) → data/sheet_seed/easy/*.csv(간사용 쉬운 머리글).

간사용 시트를 처음 꾸밀 때(또는 다시 만들 때) Apps Script(tools/sheet_setup.gs)가 이 파일들을 읽어 탭을 채운다.
"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import data  # noqa: E402

SEED = ROOT / "data" / "sheet_seed"
OUT = SEED / "easy"

# (내부 칸, 시트 머리글) — 순서가 곧 시트의 칸 순서
LAYOUT = {
    "세미나": [("제목", "제목"), ("부제", "부제 (한 줄)"), ("상태", "상태 (비우면 날짜 보고 자동)"),
             ("시작일", "시작일 (2026-11-05)"), ("종료일", "종료일"), ("장소", "장소"),
             ("강사진_id", "강사 (강사진 탭 이름)"), ("참가비", "참가비"), ("참여방법", "참여 방법"),
             ("신청_url", "신청 링크 (구글폼 주소)"), ("소개", "소개"), ("취소사유", "취소 이유"),
             ("공개", "홈피에 보이기"), ("정렬", "순서 (작을수록 위)"), ("id", "고유이름 (비워 두면 자동)")],
    "회차": [("세미나_id", "세미나 (세미나 탭 제목)"), ("회차", "회차 (1, 2, 3…)"), ("제목", "제목"),
            ("날짜", "날짜 (2026-11-05)"), ("시간", "시간 (19:00)"), ("자료_url", "자료 링크"),
            ("공개", "홈피에 보이기"), ("id", "고유이름 (비워 두면 자동)")],
    "북클럽": [("제목", "제목"), ("도서", "책"), ("상태", "상태 (비우면 날짜 보고 자동)"),
             ("날짜", "날짜 (여러 날은 ; 로 이어서)"), ("시간", "시간 (19:00)"), ("장소", "장소"),
             ("신청_url", "신청 링크 (구글폼 주소)"), ("소개", "소개"), ("취소사유", "취소 이유"),
             ("공개", "홈피에 보이기"), ("정렬", "순서 (작을수록 위)"), ("id", "고유이름 (비워 두면 자동)")],
    "강사진": [("이름", "이름"), ("소개", "소개"), ("사진_url", "사진 링크"), ("공개", "홈피에 보이기"),
             ("정렬", "순서 (작을수록 위)"), ("id", "고유이름 (비워 두면 자동)")],
    "영상": [("제목", "제목"), ("youtube_url", "유튜브 링크"), ("세미나_id", "세미나 (세미나 탭 제목)"),
           ("회차_id", "회차 (숫자)"), ("날짜", "날짜 (2026-11-05)"), ("공개", "홈피에 보이기"),
           ("정렬", "순서 (작을수록 위)"), ("id", "고유이름 (비워 두면 자동)")],
    "공지": [("제목", "제목"), ("본문", "본문"), ("링크_url", "링크"), ("게시일", "올린 날 (2026-11-05)"),
           ("공개", "홈피에 보이기"), ("정렬", "순서 (작을수록 위)"), ("id", "고유이름 (비워 두면 자동)")],
    "페이지글": [("id", "페이지 (바꾸지 마세요)"), ("제목", "제목"), ("본문", "본문"), ("공개", "홈피에 보이기")],
    "계좌": [("용도", "용도"), ("설명", "설명"), ("은행", "은행"), ("번호", "계좌번호"), ("예금주", "예금주"),
           ("안내", "안내"), ("정렬", "순서 (작을수록 위)"), ("공개", "홈피에 보이기")],
    "연락": [("항목", "항목 (바꾸지 마세요)"), ("값", "내용")],
}
FILES = {"세미나": "seminars", "회차": "sessions", "북클럽": "bookclubs", "강사진": "faculty", "영상": "videos",
         "공지": "notices", "페이지글": "pages", "계좌": "accounts", "연락": "contacts"}
PAGE_KO = {"about": "연구소 소개", "history": "걸어온 길", "people": "함께한 사람들", "archive": "지난 프로그램",
           "participate": "참여 안내", "visit": "오시는 길", "lectures": "기획강좌·특강", "agit": "아지트솜니움",
           "board": "이사회"}


def main():
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "easy_seed_in"
    tmp.mkdir(exist_ok=True)
    for stem, f in FILES.items():
        (tmp / (stem + ".csv")).write_bytes((SEED / (f + ".csv")).read_bytes())
    t = data.load_tables(tmp, resolve=False)
    fac = {r["id"]: r["이름"] for r in t["강사진"]}
    sem = {r["id"]: r["제목"] for r in t["세미나"]}
    ses = {r["id"]: r["회차"] for r in t["회차"]}
    OUT.mkdir(exist_ok=True)
    for stem, lay in LAYOUT.items():
        with open(OUT / (FILES[stem] + ".csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow([h for _, h in lay])
            for r in t.get(stem, []):
                row = []
                for c, _ in lay:
                    v = r.get(c, "")
                    if c == "강사진_id":
                        v = ", ".join(fac.get(x, x) for x in v.split(";") if x)
                    elif c == "세미나_id":
                        v = sem.get(v, v)
                    elif c == "회차_id":
                        v = ses.get(v, v)
                    elif stem == "페이지글" and c == "id":
                        v = PAGE_KO.get(v, v)
                    row.append(v)
                w.writerow(row)
    print("ok", OUT)


if __name__ == "__main__":
    main()
