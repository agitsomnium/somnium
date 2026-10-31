-- Real Postgres authorization regression. The isolated runner supplies mock auth.users/uid.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
insert into auth.users(id,email,email_confirmed_at) values
 ('10000000-0000-0000-0000-000000000001','admin@example.test',now()),
 ('10000000-0000-0000-0000-000000000002','general@example.test',now()),
 ('10000000-0000-0000-0000-000000000003','supporter@example.test',now()),
 ('10000000-0000-0000-0000-000000000004','director@example.test',null),
 ('10000000-0000-0000-0000-000000000005','other@example.test',now());
insert into classroom_private.admins(user_id) values('10000000-0000-0000-0000-000000000001');
set local role authenticated;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
select public.somnium_complete_profile('시험 관리자','1990-01-01','01000000000',true);
select pg_temp.assert_true((public.somnium_me()->>'admin')::boolean,'admin independently bootstrapped');
select public.somnium_set_director('DIRECTOR@example.test',true,true);
select public.somnium_save_lesson('20000000-0000-0000-0000-000000000001','시험 강의','소개','시험 시리즈',1,'archive',true,'youtube','abcdefghijk','');
select public.somnium_save_lesson('20000000-0000-0000-0000-000000000002','숨긴 시험 강의','소개','시험 시리즈',2,'archive',false,'vimeo','123456789','');
select pg_temp.assert_true(jsonb_array_length(public.somnium_catalog())=1,'hidden lesson omitted');
do $$begin perform public.somnium_resource('20000000-0000-0000-0000-000000000002');raise exception 'hidden exposed'; exception when insufficient_privilege then null;end$$;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000002',true);
select public.somnium_complete_profile('일반 회원','1990-01-01','01000000000',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_learn')::boolean,'general signup does not grant access');
select pg_temp.assert_true(public.somnium_catalog()='[]'::jsonb,'general catalog empty');
select public.somnium_request_supporter();
select pg_temp.assert_true((public.somnium_me()->>'supporter_state')='pending' and not (public.somnium_me()->>'can_learn')::boolean,'request alone does not grant');
select set_config('request.jwt.claims','{"user_metadata":{"role":"admin","supporter":true,"director":true}}',true);
select pg_temp.assert_true(not (public.somnium_me()->>'admin')::boolean and not (public.somnium_me()->>'can_learn')::boolean,'editable metadata ignored');
do $$begin perform public.somnium_review_supporter('10000000-0000-0000-0000-000000000002','qualified',true);raise exception 'self approved'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_set_director('general@example.test',true,true);raise exception 'self director'; exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_resource('20000000-0000-0000-0000-000000000001');raise exception 'resource exposed'; exception when insufficient_privilege then null;end$$;
do $$begin perform * from classroom_private.profiles;raise exception 'direct table exposed'; exception when insufficient_privilege then null;end$$;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000003',true);
select public.somnium_complete_profile('후원 회원','1990-01-01','01000000000',true);
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
do $$begin perform public.somnium_review_supporter('10000000-0000-0000-0000-000000000003','qualified',false);raise exception 'manual check bypassed'; exception when invalid_parameter_value then null;end$$;
select public.somnium_review_supporter('10000000-0000-0000-0000-000000000003','qualified',true);
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000003',true);
select pg_temp.assert_true((public.somnium_me()->>'can_learn')::boolean,'approved supporter allowed');
select pg_temp.assert_true((public.somnium_resource('20000000-0000-0000-0000-000000000001')->>'provider')='youtube','approved source returned');
select public.somnium_request_supporter();
select pg_temp.assert_true((public.somnium_me()->>'supporter_state')='qualified','re-request cannot overwrite approved status');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000004',true);
do $$begin perform public.somnium_complete_profile('미확인 이사','1990-01-01','01000000000',true);raise exception 'unverified accepted'; exception when insufficient_privilege then null;end$$;
select pg_temp.assert_true(public.somnium_me() is null,'unverified director denied');
reset role;
update auth.users set email_confirmed_at=now() where id='10000000-0000-0000-0000-000000000004';
set local role authenticated;
select public.somnium_complete_profile('내부 확인 회원','1990-01-01','01000000000',true);
select pg_temp.assert_true((public.somnium_me()->>'can_learn')::boolean and not (public.somnium_me()->>'admin')::boolean,'pre-registered exact email automatically learns without admin');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000005',true);
select public.somnium_complete_profile('다른 이메일','1990-01-01','01000000000',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_learn')::boolean,'different email not director');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
select public.somnium_suspend_member('10000000-0000-0000-0000-000000000004',true);
select public.somnium_suspend_member('10000000-0000-0000-0000-000000000003',true);
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000004',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_learn')::boolean,'suspension overrides director');
select public.somnium_complete_profile('재가입 시도','1990-01-01','01000000000',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_learn')::boolean,'profile resubmission cannot undo suspension');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000003',true);
select pg_temp.assert_true(not (public.somnium_me()->>'can_learn')::boolean,'suspension overrides qualified supporter with existing JWT');
do $$begin perform public.somnium_resource('20000000-0000-0000-0000-000000000001');raise exception 'suspended resource exposed'; exception when insufficient_privilege then null;end$$;
reset role;
select pg_temp.assert_true((select bool_and(relrowsecurity) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='classroom_private' and c.relkind='r'),'all private tables RLS on');
select pg_temp.assert_true(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'somnium_%' and p.prosecdef),'no elevated exposed RPCs');
set local role anon;
do $$begin perform public.somnium_catalog();raise exception 'anonymous RPC exposed'; exception when insufficient_privilege then null;end$$;
reset role;
rollback;
select 'PASS: real Postgres membership, role, metadata, source and suspension boundaries' as result;
