import csv
import datetime
import os
import re
from urllib.parse import urlparse

import sheet_friendly

SCHEMA = {
    "세미나": ["id","제목","부제","소개","상태","시작일","종료일","장소","강사진_id","신청_url","취소사유","공개","정렬","참가비","참여방법"],
    "회차": ["id","세미나_id","회차","제목","날짜","시간","자료_url","공개"],
    "북클럽": ["id","제목","도서","소개","날짜","시간","장소","신청_url","상태","취소사유","공개","정렬"],
    "강사진": ["id","이름","소개","사진_url","공개","정렬"],
    "영상": ["id","제목","youtube_url","세미나_id","회차_id","날짜","공개","정렬"],
    "공지": ["id","제목","본문","링크_url","게시일","공개","정렬"],
}

# 있어도 되고 없어도 되는 탭 — 시트에 있으면 홈페이지의 글·계좌·연락처를 시트가 덮어쓴다
OPTIONAL_SCHEMA = {
    "페이지글": ["id","제목","본문","공개"],
    "계좌": ["용도","설명","은행","번호","예금주","안내","정렬","공개"],
    "연락": ["항목","값"],
}
PAGE_IDS = ("about", "history", "people", "archive", "participate", "visit", "lectures", "agit", "board")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
STATUSES = {"예고", "모집중", "진행중", "종료", "취소"}


_DATE_ANY = re.compile(r"^\s*(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\.?(?:\s+(?:오전|오후|AM|PM)?\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)?\s*$")
_TIME_ANY = re.compile(r"^\s*(오전|오후|AM|PM|am|pm)?\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM|am|pm)?\s*$")


_MD = re.compile(r"^\s*(\d{1,2})\s*[/.월]\s*(\d{1,2})\s*일?\s*(?:\(.\))?\s*$")


def _year_for(month):
    t = _today_kst()
    y = t.year
    if month < t.month - 6:
        y += 1
    elif month > t.month + 6:
        y -= 1
    return y


def _today_kst():
    raw = os.environ.get("SITE_TODAY", "").strip()
    if raw:
        return datetime.date.fromisoformat(raw)
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date()


def norm_date(v):
    """구글 시트가 바꿔 쓴 날짜(2026. 9. 17 · 2026/9/17 · 11/12 · 11월 12일)를 2026-09-17 로. 여러 날짜는 ; 로."""
    out = []
    for part in re.split(r"[;,\n]", v or ""):
        md = _MD.match(part)
        if md and 1 <= int(md.group(1)) <= 12:
            mo, d = int(md.group(1)), int(md.group(2))
            out.append("%d-%02d-%02d" % (_year_for(mo), mo, d))
            continue
        p2 = part.strip()
        if re.fullmatch(r"\d{5}(\.0+)?", p2) and 30000 < float(p2) < 80000:  # 시트의 날짜 일련번호
            d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(p2)))
            out.append(d.isoformat())
            continue
        m = _DATE_ANY.match(part)
        out.append("%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else part.strip())
    return ";".join(x for x in out if x) if v else v


def norm_time(v):
    """오후 7:00:00 · 19:00:00 · 7:00 PM 을 19:00 으로."""
    if re.fullmatch(r"0?\.\d+", (v or "").strip()):  # 시트의 시간 소수(0.7916…)
        mins = round(float(v) * 24 * 60)
        return "%02d:%02d" % (mins // 60 % 24, mins % 60)
    k = re.fullmatch(r"\s*(오전|오후|저녁|밤|낮|아침|새벽)?\s*(\d{1,2})\s*시\s*(?:(\d{1,2})\s*분|반)?\s*", v or "")
    if k:
        h = int(k.group(2))
        mi = int(k.group(3) or (30 if "반" in (v or "") else 0))
        if k.group(1) in ("오후", "저녁", "밤") and h < 12:
            h += 12
        if k.group(1) == "낮" and h < 7:
            h += 12
        return "%02d:%02d" % (h % 24, mi)
    m = _TIME_ANY.match(v or "")
    if not m:
        return v
    h, mi = int(m.group(2)), m.group(3)
    ap = (m.group(1) or m.group(4) or "").lower()
    if ap in ("오후", "pm") and h < 12:
        h += 12
    if ap in ("오전", "am") and h == 12:
        h = 0
    return "%02d:%s" % (h, mi)


_DATE_FIELDS = {"시작일", "종료일", "날짜", "게시일"}
_TIME_FIELDS = {"시간"}


def _read_rows(stem, path, cols):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows_raw = list(csv.reader(f))
    if not rows_raw or not any(c.strip() for c in rows_raw[0]):
        raise ValueError(f"{stem}: empty file")
    header = [h.strip() for h in rows_raw[0]]
    mapping = sheet_friendly.map_header(stem, header, cols)
    if mapping is None:
        raise ValueError(f"{stem}: bad header {header!r} expected {cols!r}")
    rows = []
    for lineno, raw in enumerate(rows_raw[1:], start=2):
        row = {c: "" for c in cols}
        for c, val in zip(mapping, raw):
            if c:
                row[c] = val if c in ("본문", "소개") else val.strip()
        if sheet_friendly.is_blank(row):
            continue
        for k in row:
            if k in _DATE_FIELDS:
                row[k] = norm_date(row[k])
            elif k in _TIME_FIELDS:
                row[k] = norm_time(row[k])
        row["_line"] = lineno
        rows.append(row)
    return rows


def load_tables(data_dir, resolve=True):
    sheet_friendly.PROBLEMS.clear()
    tables = {}
    for stem, cols in SCHEMA.items():
        path = os.path.join(data_dir, stem + ".csv")
        if not os.path.isfile(path):
            raise ValueError(f"{stem}: missing file {path}")
        tables[stem] = _read_rows(stem, path, cols)
    for stem, cols in OPTIONAL_SCHEMA.items():
        path = os.path.join(data_dir, stem + ".csv")
        if not os.path.isfile(path):
            continue
        try:
            tables[stem] = _read_rows(stem, path, cols)
        except ValueError as e:
            if "empty file" in str(e):
                continue
            raise
    if resolve:
        sheet_friendly.resolve(tables, _today_kst())
    return tables


def overrides(tables):
    """시트의 선택 탭 → (페이지 글 dict, 설정 덮어쓰기 dict)."""
    pages = {}
    for r in tables.get("페이지글", []):
        if r.get("공개", "예") != "아니오" and r.get("id") in PAGE_IDS and (r.get("본문") or "").strip():
            pages[r["id"]] = r["본문"].replace("\r\n", "\n")
    cfg = {}
    accts = [r for r in tables.get("계좌", []) if r.get("공개", "예") != "아니오" and r.get("번호")]
    if accts:
        accts.sort(key=lambda r: int(r.get("정렬") or 0) if (r.get("정렬") or "0").isdigit() else 0)
        cfg["accounts"] = [{k: r[k] for k in ("용도", "설명", "은행", "번호", "예금주", "안내") if r.get(k)} for r in accts]
    keymap = {"이메일": ("email",), "CMS 정기후원 주소": ("cms_url",), "유튜브 주소": ("youtube", "url"),
              "인스타 주소": ("instagram", "url"), "페이스북 주소": ("facebook", "url"), "사이트 주소": ("site_url",)}
    for r in tables.get("연락", []):
        k, v = (r.get("항목") or "").strip(), (r.get("값") or "").strip()
        if k in keymap and v and (k == "이메일" or v.startswith("https://")):
            path = keymap[k]
            if len(path) == 1:
                cfg[path[0]] = v
            else:
                cfg.setdefault(path[0], {})[path[1]] = v
    return pages, cfg


def _err(name, i, msg):
    raise ValueError(f"{name} row {i}: {msg}")


def _check_url(name, i, field, val, required=False):
    if val == "":
        if required:
            _err(name, i, f"{field} required")
        return
    if any(c in val for c in "\r\n") or any(c.isspace() for c in val):
        _err(name, i, f"{field} whitespace/CRLF")
    p = urlparse(val)
    if p.scheme != "https" or not p.netloc:
        _err(name, i, f"{field} must be https with netloc")
    if "@" in p.netloc:
        _err(name, i, f"{field} userinfo not allowed")


def _check_youtube(name, i, val):
    if val == "":
        _err(name, i, "youtube_url required")
    if any(c in val for c in "\r\n") or any(c.isspace() for c in val):
        _err(name, i, "youtube_url whitespace/CRLF")
    p = urlparse(val)
    if p.scheme != "https" or not p.netloc:
        _err(name, i, "youtube_url must be https")
    if "@" in p.netloc:
        _err(name, i, "youtube_url userinfo not allowed")
    host = p.netloc.lower()
    vid = None
    if host == "youtu.be":
        parts = [x for x in p.path.split("/") if x]
        if len(parts) == 1:
            vid = parts[0]
    elif host in ("www.youtube.com", "youtube.com"):
        if p.path == "/watch":
            from urllib.parse import parse_qs
            q = parse_qs(p.query)
            v = q.get("v", [])
            if len(v) == 1:
                vid = v[0]
    if not vid or not YT_ID_RE.match(vid):
        _err(name, i, "youtube_url not a valid video URL")


def _check_date(name, i, field, val):
    if val == "":
        return None
    if not DATE_RE.match(val):
        _err(name, i, f"{field} bad date {val!r}")
    try:
        return datetime.date.fromisoformat(val)
    except ValueError:
        _err(name, i, f"{field} invalid date {val!r}")


def _check_time(name, i, field, val):
    if val == "":
        return
    if not TIME_RE.match(val):
        _err(name, i, f"{field} bad time {val!r}")


def _check_sort(name, i, val):
    if val == "":
        return
    if not re.match(r"^\d+$", val):
        _err(name, i, f"정렬 must be integer >=0, got {val!r}")


def validate(tables, lenient=False):
    if not lenient:
        return _validate(tables)
    dropped = {}
    fix_field = [
        (r"^(\S+) bad date|^(\S+) invalid date", None),
        (r"^(\S+) bad time", None),
        (r"^(\S+_url) (?:must|whitespace|userinfo)", None),
        (r"^정렬 must", "정렬"),
        (r"^bad 상태", "상태"),
        (r"^시작일 > 종료일", "종료일"),
    ]
    for _ in range(2000):
        try:
            out = _validate(tables)
            for k, n in dropped.items():
                total = n + len(tables.get(k, []))
                if n >= 3 and n * 2 > total:
                    raise ValueError(f"{k}: 줄 절반 이상({n}/{total})이 틀려 반영을 멈춥니다 — 머리글이 지워졌는지 보세요")
            return out
        except ValueError as e:
            m = re.match(r"^(\S+) row (\d+): (.*)$", str(e))
            if not m or m.group(1) not in tables:
                raise
            name, i, msg = m.group(1), int(m.group(2)), m.group(3)
            row = tables[name][i - 1]
            field = None
            for pat, fixed in fix_field:
                mm = re.match(pat, msg)
                if mm:
                    field = fixed or next(g for g in mm.groups() if g)
                    break
            if field == "상태":
                row["상태"] = sheet_friendly.auto_status(row, _today_kst(), ("시작일", "종료일", "날짜"))
                sheet_friendly.note(name, row, sheet_friendly.easy(msg) + " (상태는 날짜를 보고 「%s」로 올렸습니다)" % row["상태"])
                continue
            if field and field in row and row[field]:
                sheet_friendly.note(name, row, sheet_friendly.easy(msg) + " (「%s」 칸을 비우고 올렸습니다)" % field.replace("_url", " 링크"))
                row[field] = ""
                continue
            if msg.startswith("취소 requires"):
                row["취소사유"] = "사정이 생겨 열리지 않습니다"
                sheet_friendly.note(name, row, sheet_friendly.easy(msg) + " (일단 「사정이 생겨 열리지 않습니다」로 올렸습니다)")
                continue
            tables[name].pop(i - 1)
            sheet_friendly.note(name, row, sheet_friendly.easy(msg) + " (이 줄은 홈페이지에 안 나왔습니다)")
            if "unknown 세미나_id" not in msg:
                dropped[name] = dropped.get(name, 0) + 1
    raise ValueError("too many bad rows")


def _validate(tables):
    ids = {}
    for name, cols in SCHEMA.items():
        if name not in tables:
            raise ValueError(f"{name}: missing table")
        seen = set()
        for i, row in enumerate(tables[name], start=1):
            rid = row.get("id", "")
            if not ID_RE.match(rid):
                _err(name, i, f"bad id {rid!r}")
            if rid in seen:
                _err(name, i, f"duplicate id {rid!r}")
            seen.add(rid)
            pub = row.get("공개", "")
            if pub not in ("예", "아니오"):
                _err(name, i, f"공개 must be 예/아니오, got {pub!r}")
            if name == "강사진":
                if not row.get("이름", "").strip():
                    _err(name, i, "이름 required")
            else:
                if not row.get("제목", "").strip():
                    _err(name, i, "제목 required")
            _check_sort(name, i, row.get("정렬", ""))
        ids[name] = seen

    fac = ids["강사진"]
    sem = ids["세미나"]
    ses = ids["회차"]
    ses_pairs = set()
    ses_sem = {}

    for i, row in enumerate(tables["세미나"], start=1):
        st = row.get("상태", "")
        if st not in STATUSES:
            _err("세미나", i, f"bad 상태 {st!r}")
        if st == "취소" and not row.get("취소사유", "").strip():
            _err("세미나", i, "취소 requires 취소사유")
        s = _check_date("세미나", i, "시작일", row.get("시작일", ""))
        e = _check_date("세미나", i, "종료일", row.get("종료일", ""))
        if s and e and s > e:
            _err("세미나", i, "시작일 > 종료일")
        _check_url("세미나", i, "신청_url", row.get("신청_url", ""))
        refs = [x for x in row.get("강사진_id", "").split(";") if x]
        for r in refs:
            if r not in fac:
                _err("세미나", i, f"unknown 강사진_id {r!r}")
            if row["공개"] == "예":
                for fr in tables["강사진"]:
                    if fr["id"] == r and fr["공개"] != "예":
                        _err("세미나", i, f"public seminar refers hidden faculty {r!r}")

    for i, row in enumerate(tables["회차"], start=1):
        sid = row.get("세미나_id", "")
        if not sid:
            _err("회차", i, "세미나_id required")
        if sid not in sem:
            _err("회차", i, f"unknown 세미나_id {sid!r}")
        num = row.get("회차", "")
        if not re.match(r"^[1-9]\d*$", num):
            _err("회차", i, f"회차 must be positive integer, got {num!r}")
        pair = (sid, int(num))
        if pair in ses_pairs:
            _err("회차", i, f"duplicate (세미나_id,회차) {pair}")
        ses_pairs.add(pair)
        ses_sem[row["id"]] = sid
        _check_date("회차", i, "날짜", row.get("날짜", ""))
        _check_time("회차", i, "시간", row.get("시간", ""))
        _check_url("회차", i, "자료_url", row.get("자료_url", ""))
        if row["공개"] == "예":
            for sr in tables["세미나"]:
                if sr["id"] == sid and sr["공개"] != "예":
                    _err("회차", i, "public session refers hidden seminar")

    for i, row in enumerate(tables["북클럽"], start=1):
        st = row.get("상태", "")
        if st not in STATUSES:
            _err("북클럽", i, f"bad 상태 {st!r}")
        if st == "취소" and not row.get("취소사유", "").strip():
            _err("북클럽", i, "취소 requires 취소사유")
        for one in (row.get("날짜", "") or "").split(";"):
            _check_date("북클럽", i, "날짜", one.strip())
        _check_time("북클럽", i, "시간", row.get("시간", ""))
        _check_url("북클럽", i, "신청_url", row.get("신청_url", ""))

    for i, row in enumerate(tables["강사진"], start=1):
        _check_url("강사진", i, "사진_url", row.get("사진_url", ""))

    for i, row in enumerate(tables["영상"], start=1):
        _check_youtube("영상", i, row.get("youtube_url", ""))
        _check_date("영상", i, "날짜", row.get("날짜", ""))
        sid = row.get("세미나_id", "")
        rid = row.get("회차_id", "")
        if sid and sid not in sem:
            _err("영상", i, f"unknown 세미나_id {sid!r}")
        if rid:
            if rid not in ses:
                _err("영상", i, f"unknown 회차_id {rid!r}")
            if sid and ses_sem.get(rid) != sid:
                _err("영상", i, "회차_id does not belong to 세미나_id")
        if row["공개"] == "예":
            if sid:
                for sr in tables["세미나"]:
                    if sr["id"] == sid and sr["공개"] != "예":
                        _err("영상", i, "public video refers hidden seminar")
            if rid:
                for rr in tables["회차"]:
                    if rr["id"] == rid and rr["공개"] != "예":
                        _err("영상", i, "public video refers hidden session")

    for i, row in enumerate(tables["공지"], start=1):
        _check_date("공지", i, "게시일", row.get("게시일", ""))
        _check_url("공지", i, "링크_url", row.get("링크_url", ""))

    return tables


def public_rows(tables, name):
    rows = [r for r in tables[name] if r.get("공개") == "예"]
    def key(r):
        s = r.get("정렬", "")
        return (int(s) if s else 0, r["id"])
    return sorted(rows, key=key)
