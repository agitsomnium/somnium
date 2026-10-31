# 솜니움 전용 Supabase 적용 상태

2026-11-01 사용자 현재 계정에 별도 Free 조직 **솜니움** (`chtpzawbvcyxubffohbr`)과 서울 프로젝트 **somnium-classroom** (`jdfrottxrdhglxtqvtyx`)를 생성했다. 월 표시 비용 $0. 사용자 본인이 DB 비밀번호를 입력했다. 개인 Hub와 분리했다. 실제 메일·유료 서비스·운영 홈페이지 배포·도메인 변경은 하지 않았다.

## 실제 원격 적용

MCP 연결은 새 조직 접근 권한이 없어, 사용자가 로그인한 대시보드 SQL Editor에서 기존 테이블 0개를 확인한 뒤 다음을 적용했다. **native migration history에는 등록되지 않았다. 이미 적용한 기준 SQL을 다시 실행하지 않는다.**

1. `migrations/20261031154837_somnium_classroom.sql` — private 테이블과 권한검사 RPC.
2. 저장소 밖 `night-setup-20261101/cloud-lecture-import.sql` — 일부공개 강의 145개. 실제 영상 ID는 공개 저장소에 넣지 않는다.
3. `migrations/20261031162310_restrict_auto_rls_helper.sql` — 자동 RLS 이벤트 함수의 anon/authenticated 직접 실행 권한 회수. 자동 RLS 동작은 유지되는지 임시 테이블을 만들어 확인 후 rollback했다.

원격 tests/access.sql은 임시 가상 auth.users를 transaction 안에서 만들어 권한·변조·정지 경계를 검사 후 rollback, PASS. 최종 실제 Auth 사용자/회원 프로필 각 0, 강의 145, 익명 RPC 허용 0, private 전체 RLS, 회원의 직접 테이블 권한 0. Security Advisor 오류0·경고0·안내6(private 테이블 RLS에 직접 정책이 없음: RPC 전용 설계), Health 오류0·경고0. 이 시험은 실제 GoTrue OTP·SMTP·PostgREST 브라우저 통합을 검증한 것이 아니다.

코드·강의 입력 SQL·시험 기록은 작업 상위 폴더에 보관한다. **현재 자료는 운영 DB 정기 백업을 대신하지 않는다.** 원격 파괴적 rollback은 하지 않으며, 새 격리 프로젝트에 기준 SQL과 강의 입력을 적용해 재구성한다. 실제 회원 운영 시작 전 Auth 사용자·DB·Storage 원본 백업과 독립 복원을 별도로 구축해야 한다.

## 준비한 것과 검증 경계

CLI `supabase migration new somnium_classroom`으로 만든 migration과 실제 PostgreSQL 17 격리 시험(`tests/access.sql`)이다. 임시 auth.users/auth.uid는 권한 경계를 시험하기 위한 모형이다. 실제 Supabase Auth·GoTrue·PostgREST·Storage·SMTP·advisors 검증을 대체하지 않는다. Docker는 이 환경에서 확인되지 않아 Supabase 전체 로컬 스택은 실행하지 않았다.

- 회원 개인정보·관리자·후원 상태·내부 이사 이메일·강의 원본 주소·관리 이력은 비노출 classroom_private schema에 둔다. 모든 테이블 RLS 활성화, 클라이언트 테이블 직접 접근은 허용하지 않는다.
- public에는 SECURITY INVOKER RPC만 둔다. 제한된 private SECURITY DEFINER 함수는 빈 search_path, 실제 auth.uid/email_confirmed_at, 현재 DB 회원·관리자 상태로 매번 확인한다. 사용자 수정 가능한 JWT user_metadata로 권한을 정하지 않는다.
- 누구나 이메일 확인 후 일반회원 profile을 완성한다. 강의 권한은 후원 qualified 또는 내부 이메일 명단과 일치하는 이사에게 부여한다. 계정 중지는 두 자격보다 우선한다. 재가입/profile 수정으로 중지를 풀 수 없다.
- 이사 사전 명단에는 계정 생성 전에 이메일을 등록할 수 있다. 공개 이사 신청 RPC가 없고 운영관리와 회계 권한도 자동 부여하지 않는다.
- 후원금액·원장·거래내역은 저장하지 않는다. 관리자 월1만원 이상 수동 확인의 결과만 보존한다.
- 일부공개 YouTube와 Vimeo 영상 식별자를 지원한다. 자료/썸네일 경로는 private storage 연결 전까지 null이다. 저장소 policy와 업로드·다운로드 API는 아직 미구현이다. 회계/구매 기능은 이 migration에 없다.

## 전용 프로젝트 생성 후 순서

1. 솜니움이 소유·인계할 조직과 프로젝트, 개별 관리자 계정을 정한다. 결제·프로젝트 생성 전에 Free 이용 가능 슬롯과 과금 상태를 확인한다. 개인 허브 자격 정보를 재사용하지 않는다.
2. 새 프로젝트의 현재 테이블·logs·advisors와 migration 목록을 확인한다. 새 MCP 권한이 연결되면 실제 적용 상태와 migration history 차이를 먼저 확인하고, 이후 DDL은 apply_migration으로 적용·검증한다. 이미 SQL Editor에서 적용한 기준 SQL은 재실행하지 않는다. Data API에 classroom_private를 노출하지 않는다. public RPC와 grants만 사용한다.
3. 기관 SMTP 발신 도메인·발신주소·DNS 인증, Auth Site URL/허용 redirect URL, 이메일 OTP 템플릿 `{{ .Token }}`, 재발급 제한·만료 시간을 설정한다. 새 Free 프로젝트의 기본 SMTP 템플릿 제한 때문에 custom SMTP 필요 여부를 실제 대시보드에서 확인한다. 회원 정보나 시험 메일함을 공개하지 않는다.
4. 실제 frontend Auth adapter를 SDK 고정 버전으로 구현·검증한다. 가입 시 입력·동의를 받은 후 signInWithOtp(shouldCreateUser:true) → verifyOtp → somnium_complete_profile. 일반 로그인은 shouldCreateUser:false. 토큰·refresh·logout은 검증된 SDK에 맡기며 현재 Python 시험 메일함/쿠키 구현은 배포하지 않는다.
5. 첫 운영관리자는 조직 소유자가 SQL로 private admins에 명시적으로 등록한다. 프론트엔드·자기신청·user_metadata로 admin을 만들지 않는다. 이후 각 관리자도 개별 Auth 계정으로 로그인한다.
6. 실제 storage private bucket, 자료 업로드·접근검사·삭제 보유정책·짧은 signed URL 또는 전달 서버를 구현한다. 이 SQL만 적용해서 자료 보호가 완료됐다고 하지 않는다. 기관 백업·독립 복원과 auth 무효화도 필요하다.
7. 가상 계정으로 원격 Auth→RPC→영상/자료, 비회원/일반회원/보류/중지/이사/관리자, 아이폰 Safari 실기기를 검증한다. 운영 게시와 DNS 전환은 사람의 별도 지시 후다.

현재 표지의 제목 조판은 로컬 시험용이다. 실제 썸네일 제작·개별 강의의 공개 허락/자료·시리즈 분류는 검토 목록에서 확정한 뒤 반영한다. YouTube 일부공개는 링크 공유에 따른 외부 재생을 기술적으로 차단하지 못한다는 사용자 수용 범위를 유지한다. Vimeo로 이전할 때는 Embed only/숨김·허용 도메인·다운로드 설정을 계정 요금제에서 확인하고, 기존 YouTube 링크 설정 변경은 별도 확인한다.

공식 확인: https://supabase.com/docs/guides/auth/auth-email-passwordless · https://supabase.com/changelog · https://supabase.com/docs/guides/api/securing-your-api

현재 남은 핵심은 SMTP 발신 방식 확정, 실제 Auth/프로필/관리자 화면 adapter, 보호된 테스트 호스팅, private 자료 Storage와 기관 백업이다. 로컬 화면의 SQLite 변경과 원격 DB 변경은 아직 연동되지 않는다. 원격 데이터가 들어갔다는 이유로 현재 시험 서버를 인터넷에 공개하지 않는다.
