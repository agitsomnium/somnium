# 실제 Supabase 인증 연결 검토

운영 홈페이지 게시 없이 집 맥북에서만 실행하는 실제 Auth/DB 연결 화면이다.

- 새 실제 인증 화면: http://127.0.0.1:8766/
- 기존 가상 인증 검토본: http://127.0.0.1:8765/classroom/
- 공개 홈페이지 검토: http://127.0.0.1:8765/site/

현재 별도 화면만 실제 Supabase에 연결됐다. 기존 /site/ 메뉴와 가상 /classroom/은 아직 이 화면으로 교체하지 않았다.

## 실행·복구

저장소 루트에서:

```sh
npm --prefix supabase/web ci --ignore-scripts
npm --prefix supabase/web run build
python3 supabase/web/serve.py --config ../night-setup-20261101/client-config.private.json --port 8766
```

설정 파일에는 해당 전용 프로젝트 URL과 publishable 클라이언트 키만 있다. SMTP 비밀번호/secret/service_role 키/로그인 세션을 복사하지 않는다. 설정은 저장소 밖 권한 600 파일, 상위 폴더 700에 보관한다. build 결과와 node_modules는 Git 추적 대상이 아니다. 번들을 새 폴더에 clone한 뒤 위 명령으로 복구한다. 로컬 화면을 멈추거나 복원해도 운영 홈페이지에는 영향이 없다.

소스 복구는 작업 상위 night-setup-20261101/classroom-real-auth.bundle을 새 폴더에 clone한다. 이 bundle은 이후 단계의 기관 DB/Storage 정기 백업을 대신하지 않는다.

## 연결 범위

- pinned supabase-js 2.118.0, esbuild 0.28.2와 lockfile. 서버에는 비밀번호를 보내지 않고 브라우저 SDK가 Supabase OTP/세션을 처리한다. 세션은 sessionStorage에 보관하고 로그에 출력하지 않는다. 재발급은 사용자의 명시적 클릭으로만 요청한다.
- OTP 확인 → 본인 프로필·동의 → 일반회원 → 후원 확인 요청. 검토 중에는 가상 이름/생년월일/전화만 입력한다. 실제 회원 개인정보 정책의 보유·삭제 기간/문의 담당은 아직 미정이다.
- 각 요청의 실제 DB 상태로 후원/이사/중지/운영관리 권한을 확인한다. 조작 가능한 user_metadata로 권한을 부여하지 않는다.
- 관리자 회원 조회·후원 확인/보류/종료·계정 중지/재개·내부 이사 명단 등록/종료·강의 등록/수정/숨김/표시·최근 이력은 원격 RPC에 연결했다. 관리자 추가/해제는 조직 소유자의 별도 절차가 필요하다. 관리자 본인과 다른 관리자는 일반 회원 중지 API로 중지할 수 없다.
- 사용자 지정으로 솜니움 Gmail 한 계정을 첫 관리자에 등록했다. 이메일 이외 프로필은 ‘연결시험회원’ 가상 값이며 실사용 프로필로 간주하지 않는다.
- 질의응답 52개는 숨김, 강의 93개 표시. DB에는 원래 145개 기록을 남겼다. normalize(NFC) 제목 규칙으로 질의응답 게시를 거부하는 constraint를 추가했다. 실제 YouTube 설정은 변경하지 않았다.
- YouTube/Vimeo 외부 재생 URL은 승인된 RPC resource 응답으로만 구성한다. 강의 목록/출처는 공개 번들에 없으며, 145개 실제 영상 ID의 소스/번들 혼입 0건 확인. 일부공개 YouTube의 원본 링크 공유와 이미 열린 외부 플레이어 회수는 불가능하다는 사용자 수용 범위를 유지한다.
- 자료/썸네일은 아직 private Storage와 연결하지 않아 업로드·다운로드를 제공하지 않는다. 결제/회계 기능도 없다.
- testEmails는 검토 화면의 수신자 제한이며 Auth 서버 자체의 보안 허용목록은 아니다. 현재 UI에서는 솜니움 Gmail만 요청할 수 있다. 운영 전 발송 제한·봇 방지·정책과 접근 제한된 호스팅을 따로 검토한다.
- 30초마다 현재 자격을 새로 확인한다. 새 resource 요청은 매번 DB 권한을 확인하며 강의 숨김/권한 상실 시 이 화면의 플레이어와 목록을 비운다.

## 실제 검증

- 사용자 실제 Gmail 수신 및 OTP 입력 성공, browser → GoTrue → profile RPC 일반회원 가입 성공.
- 일반회원/후원 확인 요청 후 강의 목록·운영관리 화면 차단. 사용자 승인 뒤 같은 계정에 관리자 등록 → 원격 목록 145개 확인, QA 제거 후 93개.
- 실제 승인된 resource로 이전 YouTube 영상 약 15초 재생, 오류 없음. 실제 숨김 뒤 목록 144/플레이어 제거, 다시 표시해145 복구한 후 QA52개 제외.
- 원격 cloud-admin-lists.sql: 일반/대기, 후원 확인, 중지 후 차단, 독립 이사 자격, 비관리자 관리자 목록 차단, QA 게시 거부 PASS. 임시 auth.users/자격/이력 변경은 transaction rollback.
- 실제 PostgREST 익명 접근 8개 검사 모두 차단: me/catalog/resource/관리자 4개 RPC, private schema 직접 접근.
- loopback 서버 5개 경계 시험 PASS: 위조 Host/경로 탈출/비밀·소스 경로/POST 거부, CSP/no-store/검색 제외, 가상 인증 도구 없음.
- 390px 화면 scrollWidth375: 가로 넘침 없음. **아이폰 Safari 실기기 시험은 아니다.** 실제 로그아웃→새 OTP 재로그인은 이번 한 통 승인으로 반복 발송하지 않았다.
- Security Advisor 오류0, 경고1: Leaked Password Protection Disabled. 이 기능은 Pro 이상이며 현재 Free와 이메일 OTP 흐름을 유지했다. 비밀번호 가입·로그인 UI는 제공하지 않지만 플랫폼의 password API 전체를 차단했다고 주장하지 않는다. 안내6은 private 테이블 직접 정책 없음(RPC 전용 설계). 새 유료 서비스 사용 없음.

## 원격 SQL 이력과 복구 경계

MCP는 새 조직 권한이 없어 로그인 SQL Editor로 적용했다. baseline, restrict_auto_rls_helper, cloud_admin_lists, lectures_only 모두 실제 적용됐으나 native migration history에 등록되지 않았다. 이미 적용한 것을 다시 실행하지 않는다. baseline의 보안·권한을 임의로 풀지 않는다.

새 격리 프로젝트 재구성은 schema migrations를 순서대로 적용하고, 저장소 밖 cloud-lecture-import-lectures-only.sql을 사용한다. 예전 cloud-lecture-import.sql은 QA를 표시하므로 새 constraint와 충돌한다. 승인된 기관 이전·운영 복구에는 Auth 사용자·회원 권한·Storage 객체·설정·키 이관과 독립 복원 검증이 추가로 필요하다. 현재 가상 SQLite 백업은 실제 원격 Auth/DB 백업이 아니다.

공식 기준: https://supabase.com/docs/guides/auth/auth-email-passwordless · https://supabase.com/docs/guides/auth/password-security
