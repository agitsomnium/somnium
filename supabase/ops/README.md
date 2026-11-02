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

### 인터랙티브 웹 페이퍼 (1~9월부터)

회원용 본문은 `accounting_paper.html`, 자료 생성은 `build_accounting_paper.py`다. 기존 회계 엔진·원장·config를 고치지 않는다. LibreOffice는 별도의 새 작업 폴더로 변환해 재계산 사본을 만들고, 그 사본만 읽는다. 원본에 재계산 결과를 덮어쓰지 않는다. 빈 캐시를 0으로 보지 않으며, 통장·한빛누리 대사·계정 합·잔액 이월이 맞지 않으면 생성이 실패한다.

```sh
/Users/dong-hwankim/회계/.venv/bin/python supabase/ops/build_accounting_paper.py --workbook /새작업폴더/재계산사본.xlsx --previous /Users/dong-hwankim/회계/솜니움/후원현황/후원현황_2025.xlsx --through 9 --out /새작업폴더/재정보고.html
```

`--through`는 회계 담당이 대조·마감을 확인한 마지막 월을 명시한다. 자동으로 거래가 있는 마지막 월을 고르지 않는다. 현재는 9월이며, 10월은 한빛누리 자료 대기다. 다음 마감에서는 사본과 `--through`만 바꿔 새 판을 생성한다. 보고서 코드·개인정보 제외 경계는 유지한다. 2025년 비교는 후원현황의 명시된 네 가지 후원 분류만 합산한다. 작년 전체 수입·지출 비교라고 쓰지 않는다.

HTML도 같은 검토 manifest와 `sync_accounting_report.py`로 연동한다. **이번 사용자 범위는 `publish:false` 관리자 초안 저장까지**다. 일반 회원 게시 버튼은 사용자가 직접 누른다. 공개 정적 빌드에 실제 보고서·JSON·워크북을 넣지 않는다. HTML은 비공개 Storage에 있고, 기존 열람 RPC 및 다운로드 권한을 통과한 뒤 `allow-scripts allow-modals`만 있는 sandbox srcdoc 프레임에 표시된다. `allow-same-origin`, 외부 통신, 폼 전송은 허용하지 않는다. 부모 CSP도 번들에 고정된 보고서 스크립트·스타일의 SHA256만 허용하므로 템플릿 코드를 바꿀 때는 보기 앱도 다시 빌드·배포해야 한다. **자료만 갱신할 때는 보기 앱의 재배포가 필요 없다.**

초안의 실제 금액과 거래는 외부 모델로 보내지 않고 로컬 Python으로만 집계한다. 통장 메모·계좌·연락처 열은 아예 추출하지 않는다. 이름은 마스킹하며 자유 형식 텍스트는 보수적으로 비공개로 둔다. 화면 업로드는 여전히 PDF 보조 경로다.
