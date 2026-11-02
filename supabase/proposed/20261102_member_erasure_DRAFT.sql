-- DRAFT · NOT APPLIED to any database. Isolated PostgreSQL review only.
-- Problem found on the hosted test project (2026-11-02): deleting an auth user fails with HTTP 500 as soon as the member has an
-- audit row (audit.actor -> auth.users has no ON DELETE action), and series_entitlements.user_id blocks it as well.
-- Goal: an admin can erase an ordinary member (withdrawal / deletion request) in one transaction without touching other members,
-- admins, the roster, lessons, materials or series codes. Admin and approver/issuer accounts are refused (organization owner handles those).
begin;

alter table classroom_private.audit alter column actor drop not null;
alter table classroom_private.audit drop constraint audit_actor_fkey;
alter table classroom_private.audit add constraint audit_actor_fkey foreign key (actor) references auth.users(id) on delete set null;

-- Erasure ledger: what a restored pre-erasure backup needs to re-erase. Holds only one-way hashes (no name, e-mail, birth, phone or raw id)
-- plus counts of what was removed. The hashes are pseudonymous, not anonymous: someone who already holds a candidate e-mail can test it.
create table classroom_private.erasure_ledger(
 id bigint generated always as identity primary key,
 id_hash text not null unique,
 email_hash text,
 erased_at timestamptz not null default now(),
 erased_by uuid references auth.users(id) on delete set null,
 removed jsonb not null);
alter table classroom_private.erasure_ledger enable row level security;
revoke all on classroom_private.erasure_ledger from public,anon,authenticated;

create function classroom_private.erasure_hash(p text) returns text
 language sql immutable set search_path='' as $$ select encode(sha256(convert_to('somnium-erasure-v1:'||lower(p),'UTF8')),'hex') $$;

create function classroom_private.erase_member(p_user uuid) returns void
 language plpgsql security definer set search_path='' as $$
declare mail text; n_ent int; n_att int; n_aud int; n_prof int; n_sup int;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_user is null or p_user=auth.uid() then raise exception 'cannot erase this account' using errcode='22023'; end if;
 if exists(select 1 from classroom_private.admins where user_id=p_user)
  or exists(select 1 from classroom_private.supporters where checked_by=p_user)
  or exists(select 1 from classroom_private.directors where checked_by=p_user)
  or exists(select 1 from classroom_private.series_codes where issued_by=p_user) then
  raise exception 'admin or approver accounts require organization owner' using errcode='22023';
 end if;
 select email into mail from auth.users where id=p_user;
 if not found then raise exception 'member unavailable' using errcode='22023'; end if;
 if mail is not null and exists(select 1 from classroom_private.directors where email=lower(mail)) then
  raise exception 'director roster entry requires organization owner' using errcode='22023'; -- the roster keeps the e-mail; erasing around it would leave personal data behind
 end if;
 select count(*) into n_prof from classroom_private.profiles where id=p_user;
 select count(*) into n_sup from classroom_private.supporters where user_id=p_user;
 with d as (delete from classroom_private.series_entitlements where user_id=p_user returning 1) select count(*) into n_ent from d;
 with d as (delete from classroom_private.code_attempts where user_id=p_user returning 1) select count(*) into n_att from d;
 with u as (update classroom_private.audit set target='erased' where target=p_user::text or (mail is not null and lower(target)=lower(mail)) returning 1) select count(*) into n_aud from u;
 insert into classroom_private.erasure_ledger(id_hash,email_hash,erased_by,removed) values(
  classroom_private.erasure_hash(p_user::text), case when mail is null then null else classroom_private.erasure_hash(mail) end, auth.uid(),
  jsonb_build_object('profiles',n_prof,'supporter_requests',n_sup,'entitlements',n_ent,'code_attempts',n_att,'audit_targets_scrubbed',n_aud));
 delete from auth.users where id=p_user; -- cascades profile, supporter request, auth sessions; audit.actor becomes null
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'member_erased','erased');
end $$;

create function public.somnium_erase_member(p_user uuid) returns void
 language sql security invoker set search_path='' as $$ select classroom_private.erase_member(p_user) $$;
revoke all on function public.somnium_erase_member(uuid) from public,anon;
grant execute on function public.somnium_erase_member(uuid) to authenticated;
revoke all on function classroom_private.erase_member(uuid) from public,anon;
grant execute on function classroom_private.erase_member(uuid) to authenticated;

-- Operator-only (database owner / service role, never granted to authenticated): carry the ledger across a restore.
-- Restore procedure: restore the backup -> import the ledger kept outside the backup -> apply it.
create function classroom_private.export_erasure_ledger() returns jsonb
 language sql security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('id_hash',id_hash,'email_hash',email_hash,'erased_at',erased_at,'removed',removed) order by id),'[]'::jsonb) from classroom_private.erasure_ledger $$;

create function classroom_private.import_erasure_ledger(p jsonb) returns int
 language plpgsql security definer set search_path='' as $$
declare n int;
begin
 with i as (insert into classroom_private.erasure_ledger(id_hash,email_hash,erased_at,removed)
  select e->>'id_hash', e->>'email_hash', (e->>'erased_at')::timestamptz, coalesce(e->'removed','{}'::jsonb) from jsonb_array_elements(p) e
  on conflict (id_hash) do nothing returning 1) select count(*) into n from i;
 return n;
end $$;

create function classroom_private.apply_erasure_ledger() returns int
 language plpgsql security definer set search_path='' as $$
declare uid uuid; n int:=0;
begin
 for uid in select u.id from auth.users u join classroom_private.erasure_ledger l on l.id_hash=classroom_private.erasure_hash(u.id::text) loop
  if exists(select 1 from classroom_private.admins where user_id=uid) then raise exception 'ledger matches an admin account; stop and check by hand' using errcode='55000'; end if;
  delete from classroom_private.series_entitlements where user_id=uid;
  delete from classroom_private.code_attempts where user_id=uid;
  delete from auth.users where id=uid;
  n:=n+1;
 end loop;
 update classroom_private.audit a set target='erased' where a.target<>'erased' and exists(
  select 1 from classroom_private.erasure_ledger l where l.id_hash=classroom_private.erasure_hash(a.target) or l.email_hash=classroom_private.erasure_hash(a.target));
 return n;
end $$;
revoke all on function classroom_private.export_erasure_ledger(), classroom_private.import_erasure_ledger(jsonb), classroom_private.apply_erasure_ledger() from public,anon,authenticated;

commit;
