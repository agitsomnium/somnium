\set ON_ERROR_STOP on
-- Pre-erasure state used as the "backup": admin, the member to erase (profile, supporter request, entitlement, audit rows naming id and e-mail), an untouched member.
insert into auth.users(id,email,email_confirmed_at) values
 ('40000000-0000-0000-0000-000000000001','admin@example.test',now()),
 ('40000000-0000-0000-0000-000000000002','erase-me@example.test',now()),
 ('40000000-0000-0000-0000-000000000003','keep-me@example.test',now());
insert into classroom_private.admins(user_id) values('40000000-0000-0000-0000-000000000001');
insert into classroom_private.profiles(id,name,birth,phone,consent_version) values
 ('40000000-0000-0000-0000-000000000001','관리자','1980-01-01','01000000001','v1'),
 ('40000000-0000-0000-0000-000000000002','복원 삭제 대상','1990-02-03','01012345678','v1'),
 ('40000000-0000-0000-0000-000000000003','남는 회원','1991-02-03','01099999999','v1');
insert into classroom_private.supporters(user_id,state) values('40000000-0000-0000-0000-000000000002','pending'),('40000000-0000-0000-0000-000000000003','pending');
insert into classroom_private.series_codes(id,product_key,code_hash,label,issued_by) values('50000000-0000-0000-0000-000000000001','modern-capitalism-2026','\x00'::bytea,'합성','40000000-0000-0000-0000-000000000001');
insert into classroom_private.series_entitlements(user_id,product_key,code_id) values
 ('40000000-0000-0000-0000-000000000002','modern-capitalism-2026','50000000-0000-0000-0000-000000000001'),
 ('40000000-0000-0000-0000-000000000003','modern-capitalism-2026','50000000-0000-0000-0000-000000000001');
insert into classroom_private.audit(actor,action,target) values
 ('40000000-0000-0000-0000-000000000002','supporter_requested','40000000-0000-0000-0000-000000000002'),
 ('40000000-0000-0000-0000-000000000001','supporter_pending','40000000-0000-0000-0000-000000000002'),
 ('40000000-0000-0000-0000-000000000001','director_updated','erase-me@example.test'),
 ('40000000-0000-0000-0000-000000000003','supporter_requested','40000000-0000-0000-0000-000000000003');
