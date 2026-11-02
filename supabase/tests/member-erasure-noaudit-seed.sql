\set ON_ERROR_STOP on
-- Member with NO audit rows of their own: erasing them leaves no audit.actor IS NULL row, so only the ledger can block a rollback.
insert into auth.users(id,email,email_confirmed_at) values
 ('60000000-0000-0000-0000-000000000001','admin@example.test',now()),
 ('60000000-0000-0000-0000-000000000002','quiet@example.test',now());
insert into classroom_private.admins(user_id) values('60000000-0000-0000-0000-000000000001');
insert into classroom_private.profiles(id,name,birth,phone,consent_version) values
 ('60000000-0000-0000-0000-000000000001','관리자','1980-01-01','01000000001','v1'),
 ('60000000-0000-0000-0000-000000000002','조용한 회원',null,null,'v2');
