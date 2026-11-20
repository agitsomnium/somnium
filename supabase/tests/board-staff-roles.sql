-- 이사·간사 역할과 자가 신청 권한 회귀. 격리 PG(모의 auth.users/uid)에서 실행하고 끝에 rollback 한다.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
insert into auth.users(id,email,email_confirmed_at) values
 ('30000000-0000-0000-0000-000000000001','role-admin@example.test',now()),
 ('30000000-0000-0000-0000-000000000002','role-staff@example.test',now()),
 ('30000000-0000-0000-0000-000000000003','role-director@example.test',now()),
 ('30000000-0000-0000-0000-000000000004','role-general@example.test',now());
insert into classroom_private.admins(user_id) values('30000000-0000-0000-0000-000000000001');
set local role authenticated;
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000001',true);
select public.somnium_complete_profile('역할 관리자','1990-01-01','01000000000',true);
-- 간사: 자가 신청 → 승인 전에는 회계·강의 차단
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000002',true);
select public.somnium_complete_profile('시험 간사','1990-01-01','01000000000',true);
do $$begin perform public.somnium_request_role('admin');raise exception 'bad role accepted'; exception when invalid_parameter_value then null;end$$;
select public.somnium_request_role('staff');
select pg_temp.assert_true((public.somnium_me()->'role_request'->>'state')='pending' and not (public.somnium_me()->>'can_read_reports')::boolean and not (public.somnium_me()->>'can_learn')::boolean,'request alone grants nothing');
do $$begin perform public.somnium_reports();raise exception 'pending staff read reports'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_review_role_request('30000000-0000-0000-0000-000000000002',true,true);raise exception 'self approved'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_admin_role_requests();raise exception 'member listed requests'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_set_board_member('role-staff@example.test','staff',true,true);raise exception 'member edited roster'; exception when insufficient_privilege then null;end$$;
-- 관리자 승인
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000001',true);
select pg_temp.assert_true(jsonb_array_length(public.somnium_admin_role_requests())=1,'one pending request listed');
do $$begin perform public.somnium_review_role_request('30000000-0000-0000-0000-000000000002',true,false);raise exception 'approved without roster check'; exception when invalid_parameter_value then null;end$$;
do $$begin perform public.somnium_review_role_request('30000000-0000-0000-0000-000000000001',true,true);raise exception 'admin self review'; exception when insufficient_privilege then null;end$$;
select public.somnium_review_role_request('30000000-0000-0000-0000-000000000002',true,true);
select pg_temp.assert_true(public.somnium_admin_role_requests()='[]'::jsonb,'approved request leaves the pending list');
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000002',true);
select pg_temp.assert_true((public.somnium_me()->>'board_role')='staff' and (public.somnium_me()->>'can_read_reports')::boolean and (public.somnium_me()->>'can_learn')::boolean and not (public.somnium_me()->>'admin')::boolean,'approved staff reads reports and lectures without admin');
select pg_temp.assert_true(jsonb_typeof(public.somnium_reports())='array','staff lists reports');
do $$begin perform public.somnium_set_report('00000000-0000-0000-0000-000000000000',true);raise exception 'staff changed report visibility'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_request_role('director');raise exception 'registered member re-requested'; exception when invalid_parameter_value then null;end$$;
-- 이사: 관리자가 이메일로 직접 등록(기존 방식) + 역할 구분
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000001',true);
select public.somnium_set_board_member('ROLE-DIRECTOR@example.test','director',true,true);
select pg_temp.assert_true((select count(*) from jsonb_array_elements(public.somnium_admin_directors()) e where e->>'role'='staff')=1 and (select count(*) from jsonb_array_elements(public.somnium_admin_directors()) e where e->>'role'='director')=1,'roster shows one director and one staff');
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000003',true);
select public.somnium_complete_profile('시험 이사','1990-01-01','01000000000',true);
select pg_temp.assert_true((public.somnium_me()->>'board_role')='director' and (public.somnium_me()->>'can_read_reports')::boolean,'pre-registered director reads reports');
-- 일반회원: 거절되면 계속 차단, 다시 신청 가능
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000004',true);
select public.somnium_complete_profile('일반 회원','1990-01-01','01000000000',true);
select public.somnium_request_role('director');
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000001',true);
select public.somnium_review_role_request('30000000-0000-0000-0000-000000000004',false,false);
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000004',true);
select pg_temp.assert_true((public.somnium_me()->'role_request'->>'state')='declined' and public.somnium_me()->>'board_role' is null and not (public.somnium_me()->>'can_read_reports')::boolean,'declined member stays blocked');
select public.somnium_request_role('director');
select pg_temp.assert_true((public.somnium_me()->'role_request'->>'state')='pending','declined member may ask again');
-- 자격 종료 뒤에는 즉시 차단
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000001',true);
select public.somnium_set_board_member('role-staff@example.test','staff',false,false);
select set_config('request.jwt.claim.sub','30000000-0000-0000-0000-000000000002',true);
select pg_temp.assert_true(public.somnium_me()->>'board_role' is null and not (public.somnium_me()->>'can_read_reports')::boolean,'ended staff loses report access');
reset role;
rollback;
select 'PASS: board/staff roles, self-request, admin approval and report access boundaries' as result;
