import csv
import datetime
import os
import re
from urllib.parse import urlparse

SCHEMA = {
    "세미나": ["id","제목","부제","소개","상태","시작일","종료일","장소","강사진_id","신청_url","취소사유","공개","정렬"],
    "회차": ["id","세미나_id","회차","제목","날짜","시간","자료_url","공개"],
    "북클럽": ["id","제목","도서","소개","날짜","시간","장소","신청_url","상태","취소사유","공개","정렬"],
    "강사진": ["id","이름","소개","사진_url","공개","정렬"],
    "영상": ["id","제목","youtube_url","세미나_id","회차_id","날짜","공개","정렬"],
    "공지": ["id","제목","본문","링크_url","게시일","공개","정렬"],
}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
STATUSES = {"예고", "모집중", "진행중", "종료", "취소"}


def load_tables(data_dir):
    tables = {}
    for stem, cols in SCHEMA.items():
        path = os.path.join(data_dir, stem + ".csv")
        if not os.path.isfile(path):
            raise ValueError(f"{stem}: missing file {path}")
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                raise ValueError(f"{stem}: empty file")
            if header != cols:
                raise ValueError(f"{stem}: bad header {header!r} expected {cols!r}")
            rows = []
            for lineno, raw in enumerate(reader, start=2):
                if all(c.strip() == "" for c in raw):
                    continue
                if len(raw) != len(cols):
                    raise ValueError(f"{stem} row {lineno}: expected {len(cols)} fields got {len(raw)}")
                rows.append(dict(zip(cols, raw)))
        tables[stem] = rows
    return tables


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


def validate(tables):
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
        _check_date("북클럽", i, "날짜", row.get("날짜", ""))
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
