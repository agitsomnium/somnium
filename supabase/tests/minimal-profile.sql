-- Isolated PostgreSQL regression for proposed/20261101_minimal_profile_DRAFT.sql. Mock auth only.
\set ON_ERROR_STOP on
create function pg_temp.check_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
create function pg_temp.expect_error(stmt text,code text,label text) returns void language plpgsql as $$
begin execute stmt; raise exception 'FAIL: % did not fail',label;
exception when others then if sqlstate is distinct from code then raise exception 'FAIL: % got %',label,sqlstate; end if; end $$;
-- Legacy member (signed up under the old form) with birth+phone, supporter qualified, plus a series pass.
insert into auth.users(id,email,email_confirmed_at) values
 ('20000000-0000-0000-0000-000000000001','admin@example.test',now()),
 ('20000000-0000-0000-0000-000000000002','legacy@example.test',now()),
 ('20000000-0000-0000-0000-000000000003','new@example.test',now()),
 ('20000000-0000-0000-0000-000000000004','unverified@example.test',null),
 ('20000000-0000-0000-0000-000000000005','phone@example.test',now());
insert into classroom_private.admins(user_id) values('20000000-0000-0000-0000-000000000001');
insert into classroom_private.profiles(id,name,birth,phone,consent_version) values
 ('20000000-0000-0000-0000-000000000001','관리자 시험','1980-01-01','01000000001','somnium-v1-draft'),
 ('20000000-0000-0000-0000-000000000002','기존 회원','1990-02-03','01012345678','somnium-v1-draft');
insert into classroom_private.supporters(user_id,state,checked_at,checked_by) values('20000000-0000-0000-0000-000000000002','qualified',now(),'20000000-0000-0000-0000-000000000001');
insert into classroom_private.series_codes(id,product_key,code_hash,label,issued_by) values('30000000-0000-0000-0000-000000000001','modern-capitalism-2026','\x00'::bytea,'합성 코드','20000000-0000-0000-0000-000000000001');
insert into classroom_private.series_entitlements(user_id,product_key,code_id) values('20000000-0000-0000-0000-000000000003','modern-capitalism-2026','30000000-0000-0000-0000-000000000001');
create temp table before_legacy as select * from classroom_private.profiles where id='20000000-0000-0000-0000-000000000002';
create temp table before_support as select * from classroom_private.supporters where user_id='20000000-0000-0000-0000-000000000002';
\ir ../proposed/20261101_minimal_profile_DRAFT.sql
begin;
set local role authenticated;
-- unverified e-mail cannot register
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000004',true);
select pg_temp.expect_error($$select public.somnium_complete_profile_minimal('미인증 사용자',null,null,true)$$,'42501','unverified');
-- new member: name only, no phone, no birth
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000003',true);
select pg_temp.expect_error($$select public.somnium_complete_profile_minimal('새 회원',null,null,false)$$,'22023','consent required');
select pg_temp.expect_error($$select public.somnium_complete_profile_minimal('새 회원','12345',null,true)$$,'22023','bad phone');
select public.somnium_complete_profile_minimal('새 회원',null,null,true);
select pg_temp.check_true((public.somnium_me()->>'name')='새 회원','new member created with name only');
select pg_temp.check_true(public.somnium_me()->>'supporter_state'='not_requested','new member has no supporter state');
select pg_temp.check_true(public.somnium_me()->>'name'='새 회원' and (public.somnium_me()->>'can_learn')::boolean is true,'series-code holder (pre-existing entitlement) keeps seminar access after minimal sign-up');
-- phone with separators, optional supporter name
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000005',true);
select public.somnium_complete_profile_minimal('연락 회원','010-9999-0000','한빛 후원자',true);
-- legacy member re-registers with minimal form: nothing existing is erased or reset
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000002',true);
select public.somnium_complete_profile_minimal('기존 회원 개명',null,null,true);
reset role;
select pg_temp.check_true((select birth from classroom_private.profiles where id='20000000-0000-0000-0000-000000000002')=(select birth from before_legacy),'legacy birth kept');
select pg_temp.check_true((select phone from classroom_private.profiles where id='20000000-0000-0000-0000-000000000002')=(select phone from before_legacy),'legacy phone kept when none given');
select pg_temp.check_true((select consent_version from classroom_private.profiles where id='20000000-0000-0000-0000-000000000002')='somnium-v1-draft','legacy consent version kept');
select pg_temp.check_true((select state from classroom_private.supporters where user_id='20000000-0000-0000-0000-000000000002')='qualified','supporter state kept');
select pg_temp.check_true((select phone from classroom_private.profiles where id='20000000-0000-0000-0000-000000000005')='01099990000','phone normalised');
select pg_temp.check_true((select birth from classroom_private.profiles where id in ('20000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000005') limit 1) is null,'new members have no birth');
-- suspension survives re-registering
update classroom_private.profiles set suspended=true where id='20000000-0000-0000-0000-000000000005';
set local role authenticated;
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000005',true);
select public.somnium_complete_profile_minimal('연락 회원',null,null,true);
reset role;
select pg_temp.check_true((select suspended from classroom_private.profiles where id='20000000-0000-0000-0000-000000000005'),'suspension not reset by re-register');
-- admin list: no birth key, has supporter_name; non-admin and anon denied
set local role authenticated;
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000001',true);
select pg_temp.check_true(not exists(select 1 from jsonb_array_elements(public.somnium_admin_members()) m where m ? 'birth'),'admin list has no birth');
select pg_temp.check_true(exists(select 1 from jsonb_array_elements(public.somnium_admin_members()) m where m->>'supporter_name'='한빛 후원자'),'admin list has supporter name');
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000003',true);
select pg_temp.expect_error($$select public.somnium_admin_members()$$,'42501','non-admin list');
reset role;
set local role anon;
select pg_temp.expect_error($$select public.somnium_complete_profile_minimal('익명',null,null,true)$$,'42501','anon denied');
reset role;
-- old RPC still callable for compatibility (UI switch is a separate step)
select pg_temp.check_true(has_function_privilege('authenticated','public.somnium_complete_profile(text,date,text,boolean)','execute'),'legacy RPC still granted');
select 'MINIMAL PROFILE PASS' as result;
rollback;
