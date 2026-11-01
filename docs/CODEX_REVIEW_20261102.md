# Codex 검수 인계 — 솜니움 강의실 마무리 (2026-11-02, owner claude)

## 커밋·변경
- 기준 `68d6fc4`(Claude) + Codex 미커밋 수정 → 최종 `a6e45a4` (+ 문서 커밋). 브랜치 welcome-flow-20261101. 원격 push 안 함.
- a6e45a4 변경 파일: `supabase/web/app.js`, `materialDownload.js`(신규), `materialDownload.test.js`(신규, 12 시험), `build_guide.py`(«운영진 검토본»), `guide/guide-data.json`(93편 verified), `test_guide.py`, `build_static.py`+`test_static.py`(디스플레이 폰트 누락 수정·시험 추가), `ops/backup_classroom.py`, `ops/README.md`. Codex 파일은 diff를 읽고 그대로 포함했다.
- 이번에 내가 발견·수정: 정적 패키지에 `fonts/display/*`와 루트 `SomniumDisplay.woff2`가 없어 제목 서체가 대체 서체로 보였다(로컬 서버 404 11건) → 복사 추가 + «fonts-display.css의 모든 url이 패키지에 있다» 시험. 배포본에서 해당 파일 200 확인.

## 시험 (로그: final-20261102/node-tests.log, python-tests.log)
- `node --test *.test.js` 26 통과. `python3 -m unittest discover -p 'test_*.py'` 21 통과. `npm run build:all` 성공.
- DB 변경 없음 → 격리 PG 회귀는 이번에 다시 돌리지 않았다(마지막 PASS: 68d6fc4).

## 배포
- Cloudflare Pages `somnium-classroom-review`(기관 계정) 대시보드 직접 업로드(`final-20261102/classroom-review.zip`, 290 파일). 배포 `8e989f96`(직전 `0dd75f64`, 최초 Codex 배포 `f8e2bee2`/`df300de2`). wrangler 로그인은 없어 대시보드로 올렸다.
- 비로그인 curl: 메인·`/guide/`·`/runtime-config.json`·프리뷰 호스트(8e989f96…) 모두 302 → Cloudflare Access. 배포본 `app.js` 지문 앞16자 `e7233a1dfad49ff9`가 로컬 빌드와 일치.

## 실제 다운로드 근거
- 실제 이메일 인증번호(기관 메일함)로 로그인한 Chrome에서 «제6강 강의자료 · PDF 내려받기» → `~/Downloads`에 386,926B 파일 생성(`final-20261102/downloaded-제6강.pdf` 사본). `file`: PDF 1.4 11쪽, `pdftotext` 본문 열림, sha256 앞16자 `08ac87dc6fcea79e` = `series-coupons-20261101/materials-source-manifest.json` 등록 원본과 전체 지문 일치.
- **한계:** 같은 탭에서 이후 시도한 다운로드(다른 자료 2건·제6강 재시도)는 파일이 저장되지 않았다. 페이지에 심은 관찰 훅으로 앱이 `application/pdf` 386,926B blob을 만들어 `a[download]`를 클릭한 것까지는 확인했으므로(저장소 객체 11개 모두 존재·크기 정상) 앱 오류가 아니라 Chrome의 반복 자동 다운로드 제한일 가능성이 높지만, **원인을 확정하지 못했다.** 사용자가 겪은 원래 실패가 배경 새로고침 취소 때문이었는지도 확정하지 않는다. 토큰·세션 추출 우회는 하지 않았다.
- 별도 발견: 30초 새로고침이 열린 자료 패널을 닫는다(미수정).

## 화면
- 1440px(실브라우저, 배포본): 안내(제목 서체 정상)·로그인 화면·나의 강의실·강의 목록(등록 영상 93·검색 93)·관리자 영역 직접 확인. 가로 넘침 없음(scrollWidth 1425 < 1440, 스크롤바 폭).
- 390px: 이 Chrome 창은 최소 500px라 배포본에서 390을 만들 수 없었다. 같은 정적 패키지를 로컬 서버에서 Playwright 390px로 캡처: `screens/guide-390.png`(안내 전체), `screens/login-390.png`(로그인 전체), 가로 넘침 0(scrollWidth 375). 배포본 500px 창에서도 넘침 없음(485<500). **로그인 후 강의 목록·자료·관리자의 390px는 만들지 못했다.** 이것은 실기기가 아니다(아이폰 확인은 사용자 결정으로 보류).
- 1440 캡처는 대화 화면으로만 확인했고 파일로 저장하지 못했다(캡처 도구가 경로를 돌려주지 않음).

## 백업·복원
- 범위: DB 16표 258행 + Storage 11파일 → AES-256, 기관 Drive `강의실_백업`(agit.somnium 소유·제한) 업로드, 내려받아 지문 일치. 임시 PG17 복원에서 행수·파일 지문·권한(관리자/일반/익명/승인 후원회원) PASS.
- 한계: 복호화 비밀은 이 맥 키체인에만 있고 두 번째 보관 담당·기관 소유 비밀 보관 경로 미정. 실제 인증 서버(GoTrue)·메일 설정 포함 독립 복원 미검증(Auth 비밀번호·세션·SMTP 비밀 제외). 반복 백업 스케줄 없음.

## 남은 사용자 결정
`docs/최종검토_20261102.md` §4 (강사 공개·추천 순서·동의 문안, 개인정보 6항목, 백업 보관자 2인). 운영 홈페이지 연결·일반 가입 개방·삭제 SQL 원격 적용은 최종 검토 뒤.
