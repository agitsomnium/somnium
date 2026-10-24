"""간사용 시트를 «설명 없이» 쓸 수 있게 하는 층.

- 머리글을 쉬운 한글로 써도 되고(「신청 링크 (구글폼 주소)」처럼 괄호 안 설명은 무시), 칸 순서가 바뀌어도 된다.
- 고유이름(id)은 비워 두면 자동으로 정한다.
- 강사는 강사진 탭의 «이름», 세미나는 세미나 탭의 «제목»을 그대로 적으면 된다.
- 보이기 칸은 체크박스(TRUE/FALSE)·예/아니오·O/X 무엇이든 된다. 비우면 «보이기».
- 상태를 비우면 날짜를 보고 예고·모집중·진행중·종료를 정한다.
- 틀린 줄은 홈페이지 전체를 멈추지 않고 그 줄만 빠지며, 이유를 쉬운 말로 남긴다(PROBLEMS).
"""
import datetime
import hashlib
import re

PROBLEMS = []  # (탭, 줄, 제목, 쉬운 말)

COMMON = {
    "고유이름": "id", "홈피에보이기": "공개", "보이기": "공개", "순서": "정렬", "취소이유": "취소사유",
    "신청링크": "신청_url", "자료링크": "자료_url", "사진링크": "사진_url", "유튜브링크": "youtube_url",
    "올린날": "게시일", "게시날짜": "게시일",
}
TABLE = {
    "세미나": {"강사": "강사진_id", "이끔이": "강사진_id"},
    "회차": {"세미나": "세미나_id"},
    "북클럽": {"책": "도서", "강사": "이끔이"},
    "강사진": {},
    "영상": {"세미나": "세미나_id", "회차": "회차_id"},
    "공지": {"링크": "링크_url"},
    "페이지글": {"페이지": "id"},
    "계좌": {"계좌번호": "번호"},
    "연락": {"내용": "값", "주소": "값"},
}
PAGE_NAMES = {"연구소소개": "about", "소개": "about", "걸어온길": "history", "연혁": "history",
              "함께한사람들": "people", "사람들": "people", "지난프로그램": "archive", "자료실": "archive",
              "참여안내": "participate", "참여하기": "participate", "오시는길": "visit",
              "기획강좌특강": "lectures", "기획강좌": "lectures", "특강": "lectures",
              "아지트솜니움": "agit", "아지트": "agit", "이사회": "board"}
PREFIX = {"세미나": "s", "북클럽": "book", "강사진": "p", "영상": "v", "공지": "n"}
CONTENT_SKIP = {"공개", "정렬", "상태", "id"}


def _norm(h):
    h = re.sub(r"\(.*?\)|（.*?）|\[.*?\]", "", h or "")
    return re.sub(r"[\s*★✔︎✓·]+", "", h).strip() if h.strip() else ""


def map_header(stem, header, cols):
    """시트 머리글 → 내부 칸 이름(모르는 칸은 None). 아무것도 못 알아보면 None."""
    known = {c: c for c in cols}
    known.update({_norm(c): c for c in cols})
    for k, v in COMMON.items():
        if v in cols:
            known[k] = v
    for k, v in TABLE.get(stem, {}).items():
        if v in cols:
            known[k] = v
    out, used = [], set()
    for h in header:
        n = _norm(h)
        c = known.get(h.strip()) or known.get(n)
        if c in used:
            c = None
        out.append(c)
        if c:
            used.add(c)
    if not used:
        return None
    return out


def note(stem, row, msg):
    PROBLEMS.append((stem, row.get("_line", ""), (row.get("제목") or row.get("이름") or row.get("항목") or "").strip(), msg))


def is_blank(row):
    return all(not (v or "").strip() for k, v in row.items() if k not in CONTENT_SKIP and not k.startswith("_"))


def yes_no(v):
    s = (v or "").strip().lower()
    if s in ("", "예", "네", "o", "○", "yes", "y", "true", "보이기", "공개", "1"):
        return "예"
    if s in ("아니오", "아니요", "아뇨", "x", "×", "no", "n", "false", "숨기기", "비공개", "0"):
        return "아니오"
    return v


def _slug(stem, title, taken):
    t = (title or "").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", t).strip("-") if re.fullmatch(r"[\x00-\x7f]+", t) else ""
    if not base:
        base = "%s-%s" % (PREFIX.get(stem, "x"), hashlib.md5(t.encode()).hexdigest()[:6])
    cand, n = base, 2
    while cand in taken:
        cand, n = "%s-%d" % (base, n), n + 1
    return cand


def _dates(row, *fields):
    out = []
    for f in fields:
        for p in (row.get(f) or "").split(";"):
            p = p.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
                out.append(p)
    return sorted(out)


def auto_status(row, today, fields):
    ds = _dates(row, *fields)
    if not ds:
        return "예고"
    t = today.isoformat()
    if ds[-1] < t:
        return "종료"
    if ds[0] <= t:
        return "진행중"
    return "모집중"


def resolve(tables, today=None):
    """쉬운 입력을 내부 꼴로 바꾼다. load_tables 바로 뒤에 부른다."""
    today = today or datetime.date.today()
    for stem, rows in tables.items():
        for r in rows:
            if "공개" in r:
                r["공개"] = yes_no(r["공개"])
            if "정렬" in r:
                r["정렬"] = re.sub(r"\.0+$", "", (r["정렬"] or "").strip())
    # 페이지 이름(한글) → id
    for r in tables.get("페이지글", []):
        k = _norm(r.get("id", ""))
        if k in PAGE_NAMES:
            r["id"] = PAGE_NAMES[k]
    # 고유이름 자동
    for stem in ("강사진", "세미나", "북클럽", "공지"):
        rows = tables.get(stem, [])
        taken = {r["id"] for r in rows if r.get("id")}
        for r in rows:
            if not (r.get("id") or "").strip():
                r["id"] = _slug(stem, r.get("제목") or r.get("이름"), taken)
                taken.add(r["id"])
    # 강사 이름 → id
    fac = tables.get("강사진", [])
    by_name = {}
    for f in fac:
        by_name[f["id"]] = f["id"]
        by_name[re.sub(r"\s+", "", f.get("이름", ""))] = f["id"]
    for r in tables.get("세미나", []):
        raw = r.get("강사진_id") or ""
        if not raw.strip():
            continue
        ids = []
        for part in re.split(r"[;,/、·]", raw):
            p = re.sub(r"\s+|교수|선생님|목사님|님$", "", part)
            if not p:
                continue
            if p in by_name:
                ids.append(by_name[p])
            else:
                note("세미나", r, "강사 「%s」를 강사진 탭에서 못 찾아 강사 이름을 빼고 올렸습니다. 강사진 탭에 그 이름을 적으면 다음 반영 때 붙습니다." % part.strip())
        r["강사진_id"] = ";".join(dict.fromkeys(ids))
    # 세미나 제목 → id
    sems = tables.get("세미나", [])
    sem_key = {}
    for s in sems:
        sem_key[s["id"]] = s["id"]
        sem_key[re.sub(r"\s+", "", s.get("제목", ""))] = s["id"]
    def sem_of(v):
        v = (v or "").strip()
        return sem_key.get(v) or sem_key.get(re.sub(r"\s+", "", v)) or v
    for r in tables.get("회차", []):
        r["세미나_id"] = sem_of(r.get("세미나_id"))
        r["회차"] = re.sub(r"\D", "", r.get("회차") or "") or (r.get("회차") or "")
    taken = {r["id"] for r in tables.get("회차", []) if r.get("id")}
    for r in tables.get("회차", []):
        if not (r.get("id") or "").strip():
            base = "%s-%s" % (r.get("세미나_id") or "x", r.get("회차") or "0")
            cand, n = base, 2
            while cand in taken:
                cand, n = "%s-%d" % (base, n), n + 1
            r["id"] = cand
            taken.add(cand)
        if not (r.get("제목") or "").strip() and r.get("회차"):
            r["제목"] = "%s회" % r["회차"]
    ses_key = {(r["세미나_id"], r.get("회차")): r["id"] for r in tables.get("회차", [])}
    ses_ids = {r["id"] for r in tables.get("회차", [])}
    vids = tables.get("영상", [])
    taken = {r["id"] for r in vids if r.get("id")}
    for r in vids:
        r["세미나_id"] = sem_of(r.get("세미나_id")) if (r.get("세미나_id") or "").strip() else ""
        rid = (r.get("회차_id") or "").strip()
        if rid and rid not in ses_ids:
            num = re.sub(r"\D", "", rid)
            r["회차_id"] = ses_key.get((r["세미나_id"], num), rid)
        if not (r.get("id") or "").strip():
            m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", r.get("youtube_url") or "")
            r["id"] = _slug("영상", m.group(1).lower() if m else r.get("제목"), taken)
            taken.add(r["id"])
    # 세미나 날짜·상태 자동
    by_sem = {}
    for r in tables.get("회차", []):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("날짜") or ""):
            by_sem.setdefault(r["세미나_id"], []).append(r["날짜"])
    for s in sems:
        ds = sorted(by_sem.get(s["id"], []))
        if ds and not (s.get("시작일") or "").strip():
            s["시작일"] = ds[0]
        if ds and not (s.get("종료일") or "").strip():
            s["종료일"] = ds[-1]
        if not (s.get("상태") or "").strip():
            s["상태"] = auto_status(s, today, ("시작일", "종료일"))
    for b in tables.get("북클럽", []):
        if not (b.get("상태") or "").strip():
            b["상태"] = auto_status(b, today, ("날짜",))
    # 숨긴 세미나·회차에 딸린 것은 함께 숨김
    hidden_sem = {s["id"] for s in sems if s.get("공개") == "아니오"}
    for r in tables.get("회차", []):
        if r.get("세미나_id") in hidden_sem:
            r["공개"] = "아니오"
    hidden_ses = {r["id"] for r in tables.get("회차", []) if r.get("공개") == "아니오"}
    hidden_fac = {f["id"] for f in fac if f.get("공개") == "아니오"}
    for s in sems:
        if s.get("강사진_id"):
            s["강사진_id"] = ";".join(i for i in s["강사진_id"].split(";") if i not in hidden_fac)
    for r in vids:
        if r.get("세미나_id") in hidden_sem or r.get("회차_id") in hidden_ses:
            r["공개"] = "아니오"
    return tables


EASY = [
    (r"bad id", "고유이름은 영어 소문자·숫자·- 만 됩니다. 비워 두면 자동으로 정해집니다."),
    (r"duplicate id", "같은 고유이름이 두 줄에 있습니다. 한쪽 고유이름 칸을 비워 주세요."),
    (r"공개 must", "보이기 칸은 체크하거나 비워 두세요(예/아니오도 됩니다)."),
    (r"(제목|이름) required", "제목(이름) 칸이 비어 있습니다."),
    (r"정렬 must", "순서 칸에는 숫자만 적어 주세요."),
    (r"bad 상태", "상태는 목록(예고·모집중·진행중·종료·취소)에서 고르거나 비워 두세요."),
    (r"취소 requires", "상태가 취소면 취소 이유를 적어 주세요."),
    (r"(bad|invalid) date", "날짜를 못 읽었습니다. 2026-11-05 처럼 적어 주세요(여러 날은 ; 로 이어서)."),
    (r"시작일 > 종료일", "시작일이 종료일보다 늦습니다."),
    (r"bad time", "시간을 못 읽었습니다. 19:00 처럼 적어 주세요."),
    (r"youtube_url", "유튜브 링크가 영상 주소가 아닙니다. 영상 화면 주소창의 주소를 그대로 붙여 넣어 주세요."),
    (r"must be https|userinfo", "링크는 https:// 로 시작하는 주소 전체를 붙여 넣어 주세요."),
    (r"whitespace", "링크 안에 띄어쓰기가 있습니다."),
    (r"unknown 세미나_id|세미나_id required", "세미나 칸에 세미나 탭의 제목을 그대로 적어 주세요."),
    (r"unknown 회차_id|does not belong", "회차 칸은 그 세미나의 회차 숫자(1, 2, 3…)로 적어 주세요."),
    (r"회차 must", "회차 칸에는 1, 2, 3 같은 숫자를 적어 주세요."),
    (r"duplicate \(세미나_id", "같은 세미나에 같은 회차 번호가 두 줄 있습니다."),
    (r"unknown 강사진_id", "강사 이름을 강사진 탭에서 못 찾았습니다."),
    (r"hidden", "연결된 세미나·회차가 숨김이라 함께 숨겼습니다."),
]


def easy(msg):
    for pat, txt in EASY:
        if re.search(pat, msg):
            return txt
    return msg


def check_csv(today=None):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    stamp = (today or datetime.datetime.utcnow() + datetime.timedelta(hours=9))
    w.writerow(["탭", "줄", "제목", "고칠 것"])
    if not PROBLEMS:
        w.writerow(["✓", "", "문제 없음", "마지막 확인 %s" % stamp.strftime("%Y-%m-%d %H:%M")])
    for p in PROBLEMS:
        w.writerow(list(p))
    return buf.getvalue()
