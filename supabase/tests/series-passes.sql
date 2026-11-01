-- Hosted/local SQL regression. Synthetic users and Storage metadata roll back.
-- This verifies RLS decisions, not physical Storage file transfer.
begin;
select set_config('storage.operation','storage.object.get_authenticated',true);
create function pg_temp.check_true(value boolean,label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'FAIL: %',label;end if;end$$;
do $$declare a uuid;l uuid;other uuid;begin
 select user_id into strict a from classroom_private.admins where enabled;
 select lesson_id into strict l from classroom_private.series_lessons order by lesson_id limit 1;
 perform set_config('somnium.test_admin',a::text,true);perform set_config('somnium.test_lesson',l::text,true);
 insert into classroom_private.lessons(title,series_title,position,era,published,provider,video_id) values('별도 시험 강의','별도 시험',1,'archive',true,'youtube','abcdefghijk') returning id into other;
 perform set_config('somnium.test_other',other::text,true);
 perform set_config('request.jwt.claim.sub',a::text,true);
end$$;
insert into auth.users(id,email,email_confirmed_at) values
 ('91000000-0000-0000-0000-000000000001','series-one@example.test',now()),
 ('91000000-0000-0000-0000-000000000002','series-two@example.test',now()),
 ('91000000-0000-0000-0000-000000000003','series-three@example.test',now()),
 ('91000000-0000-0000-0000-000000000004','series-unverified@example.test',null);
insert into classroom_private.profiles(id,name,birth,phone,consent_version)
 select id,'가상 수강생','2000-01-01','01000000000','test' from auth.users where email like 'series-%@example.test';
insert into storage.objects(bucket_id,name) values('somnium-materials','92000000-0000-0000-0000-000000000001.pdf'),('somnium-materials','92000000-0000-0000-0000-000000000002.pdf'),('somnium-materials','92000000-0000-0000-0000-000000000003.pdf');
insert into classroom_private.materials(lesson_id,product_key,title,filename,storage_path) values
 (current_setting('somnium.test_lesson')::uuid,null,'시험 회차자료','회차.pdf','92000000-0000-0000-0000-000000000001.pdf'),
 (null,'modern-capitalism-2026','시험 추가자료','추가.pdf','92000000-0000-0000-0000-000000000002.pdf'),
 (current_setting('somnium.test_other')::uuid,null,'시험 다른자료','다른.pdf','92000000-0000-0000-0000-000000000003.pdf');
set local role authenticated;
do $$declare c jsonb;begin c:=public.somnium_issue_code('공통 코드 시험');perform set_config('somnium.test_code',c->>'code',true);perform set_config('somnium.test_code_id',c->>'id',true);end$$;
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000001',true);end$$;
select pg_temp.check_true(public.somnium_catalog()='[]'::jsonb,'general sees no catalog');
select pg_temp.check_true((select count(*)=0 from storage.objects where bucket_id='somnium-materials'),'general storage denied');
select pg_temp.check_true(not(public.somnium_redeem_code('wrong-code')->>'ok')::boolean,'wrong code denied');
do $$begin perform public.somnium_issue_code('self issue');raise exception 'member issued code';exception when insufficient_privilege then null;end$$;
do $$begin perform public.somnium_admin_series();raise exception 'member read codes';exception when insufficient_privilege then null;end$$;
select pg_temp.check_true((public.somnium_redeem_code(current_setting('somnium.test_code'))->>'ok')::boolean,'first member redeems');
select pg_temp.check_true((public.somnium_redeem_code(lower(current_setting('somnium.test_code')))->>'ok')::boolean,'same member idempotent');
select pg_temp.check_true(jsonb_array_length(public.somnium_catalog())=6,'series member sees exactly six');
select pg_temp.check_true((public.somnium_me()->>'can_learn')::boolean and not(public.somnium_me()->>'full_access')::boolean,'series entitlement never full access');
select pg_temp.check_true(public.somnium_resource(current_setting('somnium.test_lesson')::uuid) is not null,'series resource allowed');
do $$begin perform public.somnium_resource(current_setting('somnium.test_other')::uuid);raise exception 'other lecture leaked';exception when insufficient_privilege then null;end$$;
select pg_temp.check_true((select count(*)=2 from jsonb_array_elements(public.somnium_materials(current_setting('somnium.test_lesson')::uuid)) m where m->>'storage_path' like '92000000%'),'lesson and extra materials');
select pg_temp.check_true((select count(*)=2 from storage.objects where name like '92000000%'),'only own storage materials');
select set_config('storage.operation','object.get_authenticated_info',true);
select pg_temp.check_true((select count(*)=2 from storage.objects where name like '92000000%'),'legacy authenticated download supported');
select set_config('storage.operation','storage.object.sign',true);
select pg_temp.check_true((select count(*)=0 from storage.objects where name like '92000000%'),'signed URL creation denied');
select set_config('storage.operation','storage.object.list',true);
select pg_temp.check_true((select count(*)=0 from storage.objects where name like '92000000%'),'raw object listing denied');
select set_config('storage.operation','storage.object.get_authenticated',true);
do $$begin insert into storage.objects(bucket_id,name) values('somnium-materials','92000000-0000-0000-0000-000000000004.pdf');raise exception 'member upload';exception when insufficient_privilege then null;end$$;
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000002',true);end$$;
select pg_temp.check_true((public.somnium_redeem_code(current_setting('somnium.test_code'))->>'ok')::boolean,'same common code second member');
do $$begin perform set_config('request.jwt.claim.sub',current_setting('somnium.test_admin'),true);end$$;
select pg_temp.check_true((select count(*)=2 from jsonb_array_elements(public.somnium_admin_series()->'entitlements') e where e->>'email' in ('series-one@example.test','series-two@example.test')),'only one entitlement per member');
select public.somnium_set_code(current_setting('somnium.test_code_id')::uuid,false);
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000003',true);end$$;
select pg_temp.check_true(not(public.somnium_redeem_code(current_setting('somnium.test_code'))->>'ok')::boolean,'closed code blocks new registration');
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000002',true);end$$;
select pg_temp.check_true(jsonb_array_length(public.somnium_catalog())=6,'closing code retains registered access');
do $$begin perform set_config('request.jwt.claim.sub',current_setting('somnium.test_admin'),true);end$$;
select public.somnium_set_code(current_setting('somnium.test_code_id')::uuid,true);
select public.somnium_set_entitlement('91000000-0000-0000-0000-000000000001',false);
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000001',true);end$$;
select pg_temp.check_true(public.somnium_catalog()='[]'::jsonb,'revoked entitlement empty');
select pg_temp.check_true(not(public.somnium_redeem_code(current_setting('somnium.test_code'))->>'ok')::boolean,'code cannot undo revocation');
select pg_temp.check_true((select count(*)=0 from storage.objects where name like '92000000%'),'revocation blocks downloads');
do $$begin perform set_config('request.jwt.claim.sub',current_setting('somnium.test_admin'),true);end$$;
select public.somnium_suspend_member('91000000-0000-0000-0000-000000000002',true);
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000002',true);end$$;
select pg_temp.check_true(public.somnium_catalog()='[]'::jsonb,'suspension beats series');
select pg_temp.check_true((select count(*)=0 from storage.objects where name like '92000000%'),'suspension blocks downloads');
do $$begin perform public.somnium_redeem_code(current_setting('somnium.test_code'));raise exception 'suspended redeem';exception when insufficient_privilege then null;end$$;
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000004',true);end$$;
do $$begin perform public.somnium_redeem_code(current_setting('somnium.test_code'));raise exception 'unverified redeem';exception when insufficient_privilege then null;end$$;
do $$begin perform set_config('request.jwt.claim.sub','91000000-0000-0000-0000-000000000003',true);end$$;
do $$begin for i in 1..10 loop perform public.somnium_redeem_code('wrong');end loop;end$$;
select pg_temp.check_true(public.somnium_redeem_code(current_setting('somnium.test_code'))->>'reason'='wait','rate limited even valid code after guessing');
reset role;
select pg_temp.check_true((select not public from storage.buckets where id='somnium-materials'),'bucket private');
select pg_temp.check_true(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'somnium_%' and p.prosecdef),'all public RPC invokers');
set local role anon;
do $$begin perform public.somnium_redeem_code('wrong');raise exception 'anonymous redeem';exception when insufficient_privilege then null;end$$;
reset role;
rollback;
select 'PASS: shared code, six-lecture scope, duplicate use, registration closure, revocation, suspension, unverified/anonymous/admin boundaries, attempt limit, private Storage RLS' as result;
