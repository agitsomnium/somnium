\set ON_ERROR_STOP on
create function pg_temp.check_true(value boolean,label text) returns void language plpgsql as $$ begin if value is distinct from true then raise exception 'FAIL: %',label; end if; end $$;
create function pg_temp.expect_error(stmt text,code text,label text) returns void language plpgsql as $$
begin execute stmt; raise exception 'FAIL: % did not fail',label;
exception when others then if sqlstate is distinct from code then raise exception 'FAIL: % got %',label,sqlstate; end if; end $$;
insert into auth.users(id,email,email_confirmed_at) values
 ('20000000-0000-0000-0000-000000000001','admin@example.test',now()),
 ('20000000-0000-0000-0000-000000000002','member@example.test',now()),
 ('20000000-0000-0000-0000-000000000003','other@example.test',now()),
 ('20000000-0000-0000-0000-000000000004','plain@example.test',now());
insert into classroom_private.admins(user_id) values('20000000-0000-0000-0000-000000000001');
insert into classroom_private.profiles(id,name,birth,phone,consent_version) values
 ('20000000-0000-0000-0000-000000000001','관리자','1980-01-01','01000000001','v1'),
 ('20000000-0000-0000-0000-000000000002','삭제 대상','1990-02-03','01012345678','v1'),
 ('20000000-0000-0000-0000-000000000003','다른 회원','1991-02-03','01099999999','v1'),
 ('20000000-0000-0000-0000-000000000004','일반 회원',null,null,'v2');
insert into classroom_private.supporters(user_id,state) values('20000000-0000-0000-0000-000000000002','pending'),('20000000-0000-0000-0000-000000000003','pending');
insert into classroom_private.audit(actor,action,target) values
 ('20000000-0000-0000-0000-000000000002','supporter_requested','20000000-0000-0000-0000-000000000002'),
 ('20000000-0000-0000-0000-000000000003','supporter_requested','20000000-0000-0000-0000-000000000003'),
 ('20000000-0000-0000-0000-000000000001','supporter_pending','20000000-0000-0000-0000-000000000002'),
 ('20000000-0000-0000-0000-000000000001','director_updated','member@example.test');
insert into classroom_private.series_codes(id,product_key,code_hash,label,issued_by) values('30000000-0000-0000-0000-000000000001','modern-capitalism-2026','\x00'::bytea,'합성','20000000-0000-0000-0000-000000000001');
insert into classroom_private.series_entitlements(user_id,product_key,code_id) values('20000000-0000-0000-0000-000000000002','modern-capitalism-2026','30000000-0000-0000-0000-000000000001'),('20000000-0000-0000-0000-000000000003','modern-capitalism-2026','30000000-0000-0000-0000-000000000001');
-- baseline defect: plain delete fails before the draft
select pg_temp.expect_error($$delete from auth.users where id='20000000-0000-0000-0000-000000000003'$$,'23503','audit FK blocks plain delete (pre-draft behaviour)');
\ir ../proposed/20261102_member_erasure_DRAFT.sql
create temp table before_other as select * from classroom_private.profiles where id='20000000-0000-0000-0000-000000000003';
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000004',true);
select pg_temp.expect_error($$select public.somnium_erase_member('20000000-0000-0000-0000-000000000002')$$,'42501','non-admin refused');
select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000001',true);
select pg_temp.expect_error($$select public.somnium_erase_member('20000000-0000-0000-0000-000000000001')$$,'22023','self refused');
select pg_temp.expect_error($$select public.somnium_erase_member('00000000-0000-0000-0000-0000000000ff')$$,'22023','unknown refused');
select public.somnium_erase_member('20000000-0000-0000-0000-000000000002');
commit;
select pg_temp.check_true(not exists(select 1 from auth.users where id='20000000-0000-0000-0000-000000000002'),'user removed');
select pg_temp.check_true(not exists(select 1 from classroom_private.profiles where id='20000000-0000-0000-0000-000000000002'),'profile (name, birth, phone) removed');
select pg_temp.check_true(not exists(select 1 from classroom_private.supporters where user_id='20000000-0000-0000-0000-000000000002'),'supporter request removed');
select pg_temp.check_true(not exists(select 1 from classroom_private.series_entitlements where user_id='20000000-0000-0000-0000-000000000002'),'entitlement removed');
select pg_temp.check_true(not exists(select 1 from classroom_private.audit where target in ('20000000-0000-0000-0000-000000000002','member@example.test') or actor='20000000-0000-0000-0000-000000000002'),'no id or e-mail left in audit');
select pg_temp.check_true(exists(select 1 from classroom_private.audit where action='member_erased' and actor='20000000-0000-0000-0000-000000000001'),'erase itself is audited without personal data');
select pg_temp.check_true((select count(*) from classroom_private.audit where action='supporter_requested')=2,'audit rows kept (actor null)');
select pg_temp.check_true((select count(*)=0 from (select * from classroom_private.profiles where id='20000000-0000-0000-0000-000000000003' except select * from before_other) x),'other member profile untouched');
select pg_temp.check_true(exists(select 1 from classroom_private.series_entitlements where user_id='20000000-0000-0000-0000-000000000003') and exists(select 1 from classroom_private.supporters where user_id='20000000-0000-0000-0000-000000000003'),'other member access untouched');
select pg_temp.check_true(exists(select 1 from classroom_private.admins) and exists(select 1 from classroom_private.series_codes),'admin and codes untouched');
begin; set local role authenticated; select set_config('request.jwt.claim.sub','20000000-0000-0000-0000-000000000001',true);
select pg_temp.expect_error($$select public.somnium_erase_member('20000000-0000-0000-0000-000000000001')$$,'22023','admin target refused');
rollback;
select 'MEMBER ERASURE PASS';
