-- 이사회 보고(활동·회계)는 관리자·이사·간사만. 후원회원·일반회원·비로그인은 목록·파일·등록·숨김 전환 모두 차단.
-- 격리 PG(모의 auth.users/uid)에서 실행하고 끝에 rollback 한다.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
insert into auth.users(id,email,email_confirmed_at) values
 ('31000000-0000-0000-0000-000000000001','iso-admin@example.test',now()),
 ('31000000-0000-0000-0000-000000000002','iso-supporter@example.test',now()),
 ('31000000-0000-0000-0000-000000000003','iso-general@example.test',now()),
 ('31000000-0000-0000-0000-000000000004','iso-staff@example.test',now());
insert into classroom_private.admins(user_id) values('31000000-0000-0000-0000-000000000001');
insert into classroom_private.accounting_reports(title,period,filename,storage_path,created_by,enabled) values
 ('공개 활동보고','2026','activity.html','aaaaaaaa-0000-0000-0000-000000000001.html','31000000-0000-0000-0000-000000000001',true),
 ('숨긴 활동보고','2026','activity.html','aaaaaaaa-0000-0000-0000-000000000002.html','31000000-0000-0000-0000-000000000001',false);
set local role authenticated;
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000001',true);
select public.somnium_complete_profile('격리 관리자','1990-01-01','01000000000',true);
select public.somnium_set_board_member('iso-staff@example.test','staff',true,true);
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000002',true);
select public.somnium_complete_profile('격리 후원','1990-01-01','01000000000',true);
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000003',true);
select public.somnium_complete_profile('격리 일반','1990-01-01','01000000000',true);
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000004',true);
select public.somnium_complete_profile('격리 간사','1990-01-01','01000000000',true);
reset role;
insert into classroom_private.supporters(user_id,state,checked_at,checked_by) values('31000000-0000-0000-0000-000000000002','qualified',now(),'31000000-0000-0000-0000-000000000001');
set local role authenticated;
-- 후원회원: 강의는 보지만 보고서는 목록·파일·등록·전환 모두 불가
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000002',true);
select pg_temp.assert_true((public.somnium_me()->>'can_learn')::boolean and not (public.somnium_me()->>'can_read_reports')::boolean,'supporter learns but has no report access');
do $$begin perform public.somnium_reports();raise exception 'supporter listed reports'; exception when insufficient_privilege then null;end$$;
select pg_temp.assert_true(not classroom_private.can_read_report('aaaaaaaa-0000-0000-0000-000000000001.html'),'supporter cannot read a published report file');
do $$begin perform public.somnium_save_report('x','','a.html','aaaaaaaa-0000-0000-0000-000000000009.html',true);raise exception 'supporter saved report'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_set_report((select '00000000-0000-0000-0000-000000000000'::uuid),true);raise exception 'supporter toggled report'; exception when insufficient_privilege then null;end$$;
do $$begin perform 1 from classroom_private.accounting_reports;raise exception 'supporter read table directly'; exception when insufficient_privilege then null;end$$;
-- 일반회원
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000003',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_read_reports')::boolean and not classroom_private.can_read_report('aaaaaaaa-0000-0000-0000-000000000001.html'),'general member has no report access');
do $$begin perform public.somnium_reports();raise exception 'general member listed reports'; exception when insufficient_privilege then null;end$$;
-- 간사: 공개된 판만, 등록·전환은 불가
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000004',true);
select pg_temp.assert_true(jsonb_array_length(public.somnium_reports())=1 and public.somnium_reports()->0->>'title'='공개 활동보고','staff sees only the published edition');
select pg_temp.assert_true(classroom_private.can_read_report('aaaaaaaa-0000-0000-0000-000000000001.html') and not classroom_private.can_read_report('aaaaaaaa-0000-0000-0000-000000000002.html'),'staff reads published file only');
do $$begin perform public.somnium_save_report('x','','a.html','aaaaaaaa-0000-0000-0000-000000000009.html',true);raise exception 'staff saved report'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_set_report((select id from (select (public.somnium_reports()->0->>'id')::uuid id) x),false);raise exception 'staff hid report'; exception when insufficient_privilege then null;end$$;
-- 관리자: 숨긴 판까지
select set_config('request.jwt.claim.sub','31000000-0000-0000-0000-000000000001',true);
select pg_temp.assert_true(jsonb_array_length(public.somnium_reports())=2,'admin sees hidden editions too');
reset role;
-- 비로그인
set local role anon;
do $$begin perform public.somnium_reports();raise exception 'anonymous listed reports'; exception when insufficient_privilege then null;end$$;
reset role;
rollback;
select 'PASS: board reports are closed to supporters, general members and anonymous visitors' as result;
