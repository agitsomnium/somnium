# Classroom backup operations

`backup_classroom.py /absolute/private/new-output-folder` reads the explicitly named Somnium test project through the existing authenticated Supabase CLI. It does not depend on a copied `w/` linked-project directory. Its output is plaintext personal data: the output directory is0700, then the authorized operator must encrypt it and remove the generated plaintext after verification. Never upload plaintext or credentials. The code does not print keys or row values.

The 2026-11-02 Codex completion run queried16 tables/258 rows and fetched11 Storage objects(7,367,016bytes). The encrypted result was decrypted into a temporary directory, restored to isolated PostgreSQL and checked against row counts, object hashes and role tests. This verifies logical DB/data restoration, not an independent running GoTrue authentication service. Auth sessions/passwords/SMTP secrets are excluded and must be provisioned separately.

Institution copy: Google Drive folder `강의실_백업`, owner agit.somnium@gmail.com, restricted to that account; upload was downloaded again and SHA256 matched. Latest file:
https://drive.google.com/file/d/1p33N1QQ_BPW-NiH5Cwm0EZ-CeQ9czx24/view
SHA256 `788d674c838c3406b1ac5af569938fdec81024fb70dab065da8880fbac0fc0c9`.

Encryption passphrase remains only in macOS Keychain service `somnium-classroom-backup-20261102`; never include its value in documents, terminal output or model inputs. A second authorized custodian and institution-owned secret vault have not been designated. A future operator must arrange that handoff securely before relying on recovery without this Mac. No recurring backup scheduler was added or claimed.

## Backup decryption + integrity check (not a restore test)
`decrypt_integrity_check.py ENCRYPTED_FILE` decrypts with a hidden passphrase prompt and verifies the manifest row counts and file hashes. It restores nothing.

## Erasure ledger (member deletion)
After the erasure draft is applied, run `erasure_ledger.py --ref <project> export --out-dir <private dir> --store-dir <institution folder>` after every deletion; only an `OK export` line counts. After restoring any backup, run `erasure_ledger.py --ref <project> apply --file <stored ledger>`; only an `OK apply` line counts. `verify` checks a stored file against the live database. Any `FAILED` line means not done. The ledger holds one-way hashes only.

## AI 회계 담당의 회원 보고 연동 (2026-11-02 사용자 결정)

당분간 사용자의 수동 업로드 대신 회계 담당 AI가 기존 월마감 작업의 마지막 단계에서 회원용 보고서를 연동한다. 새 예약·폴더 감시를 만들지 않는다. 회계 엔진 `~/회계`를 다른 창과 동시에 수정하거나 마감을 다시 실행하지 않는다.

1. 기존 회계 마감·대조가 끝난 **회원용 PDF**를 만든다. 원장·은행내역·후원자 명세·이사회 전용 자료를 그대로 선택하지 않는다. 보고서의 개인정보 제외 여부를 확인한다. 보고 기간 미완료는 명시한다.
2. 아래 manifest를 작업 폴더에 작성한다. `sha256`은 검토한 실제 PDF 전체 지문이다. `member_safe: true`는 검토 결과이며 도구가 개인정보를 자동 검사했다는 뜻이 아니다. `publish: true`는 로그인한 일반 회원에게 게시, `false`는 관리자 전용 임시 저장이다.
3. 아래 명령의 로컬 preview를 확인한 뒤 같은 manifest에 `--apply`를 붙인다. `OK sync report=...`를 확인해야 완료다. 같은 파일·제목·기간·상태로 재실행하면 중복을 만들지 않는다. 기존 기록의 제목이나 공개 여부가 다르면 자동 덮어쓰기·재공개하지 않고 실패한다.
4. 회원용 목록·PDF 열람을 확인하고, 보고 기간·파일 지문·결과 ID·미완료 항목을 회계 담당 기록에 남긴다. 새 파일로 정정하면 이전 보고서는 보존되므로 이전 판의 숨김은 별도로 확인한다.

```json
{"file":"회원용_보고서.pdf","title":"솜니움 2026년 9월 회계 보고","period":"2026-09","sha256":"실제 PDF의 sha256 64자리","member_safe":true,"publish":true}
```

```sh
python3 supabase/ops/sync_accounting_report.py --manifest /절대경로/manifest.json
python3 supabase/ops/sync_accounting_report.py --manifest /절대경로/manifest.json --apply
```

기존 로그인된 Supabase CLI를 사용하며, 기관 관리자 계정이 이미 존재해야 한다. 관리자를 새로 만들거나 일반 회원 권한을 바꾸지 않는다. 저장은 비공개 `somnium-accounting` 버킷에 하고 다운로드 바이트를 원본과 대조한다. 키는 도구 프로세스 안에서만 읽는다. 업로드 뒤 DB 등록이 실패하면 파일만 남을 수 있으며, 같은 manifest로 재실행해 확인·등록한다. 성공 전에는 완료로 보고하지 않는다. 수동 업로드 화면은 보조 경로로 유지한다.
