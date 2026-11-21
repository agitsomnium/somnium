-- 본인 탈퇴·운영자 삭제 회귀. 격리 PG(run_isolated.py)에서 실행하고 끝에 rollback 한다.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
insert into auth.users(id,email,email_confirmed_at) values
 ('32000000-0000-0000-0000-000000000001','w-admin@example.test',now()),
 ('32000000-0000-0000-0000-000000000002','w-leaver@example.test',now()),
 ('32000000-0000-0000-0000-000000000003','w-staff@example.test',now()),
 ('32000000-0000-0000-0000-000000000004','w-target@example.test',now()),
 ('32000000-0000-0000-0000-000000000005','w-other@example.test',now()),
 ('32000000-0000-0000-0000-000000000006','w-admin2@example.test',now());
insert into classroom_private.admins(user_id) values('32000000-0000-0000-0000-000000000001'),('32000000-0000-0000-0000-000000000006');
set local role authenticated;
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-00000000000'||g,true),public.somnium_complete_profile('탈퇴 시험 '||g,'1990-01-01','01000000000',true) from generate_series(1,6) g;
-- 후원 신청·간사 신청 기록을 가진 회원들
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000002',true); select public.somnium_request_supporter();
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000003',true); select public.somnium_request_role('staff');
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000004',true); select public.somnium_request_supporter();
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000001',true);
select public.somnium_review_role_request('32000000-0000-0000-0000-000000000003',true,true);
select public.somnium_review_supporter('32000000-0000-0000-0000-000000000002','qualified',true);
-- 1) 본인 탈퇴: 확인 낱말 없으면 거절, 있으면 본인 것만 사라짐
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000002',true);
do $$begin perform public.somnium_withdraw('네');raise exception 'withdrew without the word'; exception when invalid_parameter_value then null;end$$;
select public.somnium_withdraw('탈퇴');
reset role;
select pg_temp.assert_true(not exists(select 1 from auth.users where id='32000000-0000-0000-0000-000000000002')
 and not exists(select 1 from classroom_private.profiles where id='32000000-0000-0000-0000-000000000002')
 and not exists(select 1 from classroom_private.supporters where user_id='32000000-0000-0000-0000-000000000002')
 and not exists(select 1 from classroom_private.audit where target like '32000000-0000-0000-0000-000000000002%' or lower(target)='w-leaver@example.test')
 and (select count(*) from classroom_private.profiles)=5,'self withdrawal removes only that member');
select pg_temp.assert_true((select count(*)=1 and bool_and(erased_by is null and (removed->>'self')::boolean and id_hash ~ '^[0-9a-f]{64}$') from classroom_private.erasure_ledger)
 and exists(select 1 from classroom_private.audit where action='member_withdrew' and actor is null and target='erased'),'self withdrawal is in the ledger and audit without identity');
-- 2) 간사 본인 탈퇴: 명단 행도 함께 사라져 같은 메일로 다시 가입해도 자격이 돌아오지 않음
set local role authenticated;
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000003',true);
select pg_temp.assert_true((public.somnium_me()->>'can_read_reports')::boolean,'staff had report access before leaving');
select public.somnium_withdraw('탈퇴');
reset role;
select pg_temp.assert_true(not exists(select 1 from classroom_private.directors where email='w-staff@example.test') and not exists(select 1 from classroom_private.role_requests where user_id='32000000-0000-0000-0000-000000000003'),'roster row and request removed');
insert into auth.users(id,email,email_confirmed_at) values('32000000-0000-0000-0000-000000000033','w-staff@example.test',now());
set local role authenticated;
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000033',true);
select public.somnium_complete_profile('다시 가입','1990-01-01','01000000000',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_read_reports')::boolean and not (public.somnium_me()->>'can_learn')::boolean,'re-registered e-mail starts as a plain member');
-- 3) 관리자는 스스로 탈퇴 불가, 회원은 남을 지울 수 없음
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000001',true);
do $$begin perform public.somnium_withdraw('탈퇴');raise exception 'admin withdrew'; exception when invalid_parameter_value then null;end$$;
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000005',true);
do $$begin perform public.somnium_erase_member('32000000-0000-0000-0000-000000000004');raise exception 'member erased another member'; exception when insufficient_privilege then null;end$$;
do $$begin perform classroom_private.erase_account('32000000-0000-0000-0000-000000000004',null,'x');raise exception 'member reached the internal function'; exception when insufficient_privilege then null;end$$;
-- 4) 운영자 삭제: 다른 관리자·자기 자신은 거절, 일반 회원은 삭제
select set_config('request.jwt.claim.sub','32000000-0000-0000-0000-000000000001',true);
do $$begin perform public.somnium_erase_member('32000000-0000-0000-0000-000000000001');raise exception 'admin erased self'; exception when invalid_parameter_value then null;end$$;
do $$begin perform public.somnium_erase_member('32000000-0000-0000-0000-000000000006');raise exception 'admin erased another admin'; exception when invalid_parameter_value then null;end$$;
select public.somnium_erase_member('32000000-0000-0000-0000-000000000004');
select pg_temp.assert_true(not exists(select 1 from jsonb_array_elements(public.somnium_admin_members()) m where m->>'id'='32000000-0000-0000-0000-000000000004')
 and exists(select 1 from jsonb_array_elements(public.somnium_admin_members()) m where m->>'id'='32000000-0000-0000-0000-000000000005'),'erased member leaves the list; others stay');
reset role;
select pg_temp.assert_true((select count(*) from classroom_private.erasure_ledger)=3 and (select count(*) from classroom_private.erasure_ledger where erased_by='32000000-0000-0000-0000-000000000001')=1
 and classroom_private.erasure_ledger_pending()=0 and jsonb_array_length(classroom_private.export_erasure_ledger())=3
 and classroom_private.export_erasure_ledger()::text !~ '@|32000000-0000','ledger holds three hashed entries and nothing identifying');
-- 비로그인
set local role anon;
do $$begin perform public.somnium_withdraw('탈퇴');raise exception 'anonymous withdrew'; exception when insufficient_privilege then null;end$$;
reset role;
rollback;
select 'PASS: self withdrawal and operator erasure' as result;
