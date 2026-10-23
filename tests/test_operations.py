import copy
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_sheets  # noqa: E402
from build import build
from data import load_tables, validate, SCHEMA  # noqa: E402

SAMPLE = ROOT / "data" / "sample"


def _write_tables(directory, tables):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, fields in SCHEMA.items():
        rows = tables.get(name, [])
        with open(directory / (name + ".csv"), "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, restval="")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})


def _hash_tree(directory):
    h = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file():
            h.update(str(path.relative_to(directory)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()


class OpsTest(unittest.TestCase):
    def setUp(self):
        self.tables = copy.deepcopy(load_tables(SAMPLE))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.input = Path(self.tmp.name) / "input"
        self.output = ROOT / "design" / ("test-" + os.urandom(6).hex())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.output, ignore_errors=True))

    def run_build(self, tables=None):
        _write_tables(self.input, tables if tables is not None else self.tables)
        build(self.input, self.output, base="/somnium", preview=True)

    def _html_files(self):
        return [p for p in self.output.rglob("*.html")]

    def test_workflow(self):
        first = self.tables["세미나"][0]
        new = dict(first)
        new.update(id="trial", 제목="시험 세미나", 상태="모집중",
                   신청_url="https://forms.gle/ExampleOnly123")
        self.tables["세미나"].append(new)
        self.run_build()
        page = self.output / "seminars" / "trial" / "index.html"
        if not page.exists():
            page = next(p for p in self._html_files() if "trial" in str(p))
        text = page.read_text(encoding="utf-8")
        self.assertIn("시험 세미나", text)
        self.assertIn("정용택", text)
        self.assertIn("https://forms.gle/ExampleOnly123", text)

        new.update(제목="수정 세미나", 시작일="2026-10-20", 종료일="2026-11-20")
        self.run_build()
        text = page.read_text(encoding="utf-8")
        self.assertIn("수정 세미나", text)
        self.assertNotIn("시험 세미나", text)
        self.assertIn("2026-10-20", text)
        self.assertIn("2026-11-20", text)
        self.assertIn(first["제목"], (self.output / "index.html").read_text(encoding="utf-8"))

        new.update(상태="취소", 취소사유="일정 변경")
        self.run_build()
        text = page.read_text(encoding="utf-8")
        self.assertNotIn("https://forms.gle/ExampleOnly123", text)
        self.assertIn("일정 변경", text)
        self.assertIn("일정 변경", (self.output / "programs" / "index.html").read_text(encoding="utf-8"))

        new.update(상태="종료", 종료일="2026-12-20")
        self.run_build()
        text = page.read_text(encoding="utf-8")
        self.assertNotIn("https://forms.gle/ExampleOnly123", text)

        sem_id = first["id"]
        round_id = self.tables["회차"][0]["id"]
        self.tables["영상"].append({
            "id": "clip", "제목": "영상시험", "youtube_url": "https://www.youtube.com/watch?v=ABCDEFGHIJK",
            "세미나_id": sem_id, "회차_id": round_id, "날짜": "2026-01-01", "공개": "예", "정렬": "1"})
        self.run_build()
        detail = next(p for p in self._html_files() if sem_id in str(p))
        self.assertIn("ABCDEFGHIJK", detail.read_text(encoding="utf-8"))

        new.update(제목="<script>alert(1)</script>")
        self.run_build()
        text = page.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)

        hidden = dict(first)
        hidden.update(id="hidden", 제목="숨김 테스트", 공개="아니오")
        self.tables["세미나"].append(hidden)
        self.run_build()
        self.assertFalse(any("hidden" in str(p) for p in self._html_files()))
        self.assertNotIn("숨김 테스트", (self.output / "index.html").read_text(encoding="utf-8"))

        import re
        for html in self._html_files():
            body = html.read_text(encoding="utf-8")
            for attr in re.findall(r'(?:href|src)="([^"]+)"', body):
                if attr.startswith("/"):
                    self.assertTrue(attr.startswith("/somnium/"), attr)
                    relative, _, fragment = attr[len("/somnium/"):].partition("#")
                    target = self.output / relative
                    if fragment:
                        page = target / "index.html" if target.is_dir() else target
                        self.assertIn('id="' + fragment + '"', page.read_text(encoding="utf-8"))
                    self.assertTrue(target.exists(), attr)
            self.assertNotIn("backup", str(html))
            self.assertNotIn("docs", str(html))


    def test_completed_pages_and_data(self):
        self.tables["영상"].append({"id":"resource-clip","제목":"자료 연결 시험","youtube_url":"https://www.youtube.com/watch?v=ABCDEFGHIJK","세미나_id":self.tables["세미나"][0]["id"],"회차_id":"","날짜":"","공개":"예","정렬":"0"})
        self.run_build()
        about=(self.output/"about/index.html").read_text()
        self.assertEqual(about.count("<h1>"),1)
        self.assertIn("agit.somnium@gmail.com",about)
        self.assertNotIn("contact@somnium",about)
        for anchor in ("spirit","board","history","visit"):
            self.assertIn('id="'+anchor+'"',about)
        program=(self.output/"programs/index.html").read_text()
        self.assertIn("느슨한 네트워크",program)
        self.assertIn("2021-2024",program)
        archive=(self.output/"archive/index.html").read_text()
        self.assertIn("지난 프로그램",archive)
        self.assertFalse((self.output/"resources/index.html").exists())
        participate=(self.output/"participate/index.html").read_text()
        self.assertIn(self.tables["세미나"][0]["제목"],participate)
        self.assertIn("https://online.mrm.or.kr/PCjx2kb",participate)
        for f in self.output.rglob("*.html"):
            body=f.read_text()
            self.assertIn("data-theme-switch",body)
            self.assertIn("/somnium/assets/theme.js",body)

    def test_reject_preserves_output(self):
        self.run_build()
        baseline_hash = _hash_tree(self.output)
        baseline = copy.deepcopy(self.tables)
        sem = baseline["세미나"][0]
        fac = baseline["강사진"][0]
        mutations = [
            lambda t: t["세미나"][0].update(시작일="2026-02-30"),
            lambda t: t["세미나"].append(dict(t["세미나"][0])),
            lambda t: t["세미나"][0].update(강사진_id="nope"),
            lambda t: t["세미나"][0].update(신청_url="javascript:alert(1)"),
            lambda t: t["세미나"][0].update(상태="취소", 취소사유=""),
            lambda t: t["강사진"][0].update(공개="아니오"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tables = copy.deepcopy(baseline)
                mutate(tables)
                with self.assertRaises(ValueError):
                    self.run_build(tables)
                self.assertEqual(baseline_hash, _hash_tree(self.output))

        bad = Path(self.tmp.name) / "bad"
        bad.mkdir()
        (bad / "세미나.csv").write_text("id,제목\nx,y\n", encoding="utf-8")
        with self.assertRaises(Exception):
            load_tables(bad)

    def test_fetch_and_cli(self):
        self.assertTrue(fetch_sheets._valid_url(
            "https://docs.google.com/spreadsheets/d/e/abc/pub?output=csv&gid=0"))
        self.assertTrue(fetch_sheets._valid_url(
            "https://docs.google.com/spreadsheets/d/abc/export?format=csv&gid=0"))
        self.assertFalse(fetch_sheets._valid_url("http://evil.com/x"))
        self.assertFalse(fetch_sheets._valid_url("https://accounts.google.com/login"))

        root = Path(self.tmp.name) / "root"
        live = root / "data" / "live"
        live.mkdir(parents=True)
        marker = live / "marker.txt"
        marker.write_text("keep", encoding="utf-8")
        cfg = Path(self.tmp.name) / "config.json"
        cfg.write_text(json.dumps({}), encoding="utf-8")
        with mock.patch.object(fetch_sheets, "ROOT", root):
            with self.assertRaisesRegex(Exception, "config"):
                fetch_sheets.fetch_all(cfg, live)
        self.assertTrue(marker.exists())

        urls = {name: "https://docs.google.com/spreadsheets/d/e/x/pub?output=csv&gid=%d" % i
                for i, name in enumerate(SCHEMA)}
        cfg.write_text(json.dumps(urls), encoding="utf-8")
        bad_tables = copy.deepcopy(self.tables)
        bad_tables["세미나"][0]["시작일"] = "2026-02-30"

        def fake_fetch(url):
            name = next(n for n, u in urls.items() if u == url)
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=SCHEMA[name], restval="")
            w.writeheader()
            for row in bad_tables.get(name, []):
                w.writerow({k: row.get(k, "") for k in SCHEMA[name]})
            return buf.getvalue()

        with mock.patch.object(fetch_sheets, "ROOT", root), \
                mock.patch.object(fetch_sheets, "fetch_csv", side_effect=fake_fetch):
            with self.assertRaisesRegex(ValueError, "날짜|시작일|date"):
                fetch_sheets.fetch_all(cfg, live)
        self.assertTrue(marker.exists())

        bad_tables = copy.deepcopy(self.tables)
        with mock.patch.object(fetch_sheets, "ROOT", root), \
                mock.patch.object(fetch_sheets, "fetch_csv", side_effect=fake_fetch):
            fetch_sheets.fetch_all(cfg, live)
        self.assertFalse(marker.exists())
        self.assertEqual(validate(load_tables(live)), self.tables)

        out = ROOT / "design" / ("test-" + os.urandom(6).hex())
        self.addCleanup(lambda: __import__("shutil").rmtree(out, ignore_errors=True))
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"), "--sample", "--output", str(out)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((out / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
