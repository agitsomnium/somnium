-- DRAFT · NOT APPLIED to any database. Isolated PostgreSQL review only.
-- Problem found on the hosted test project (2026-11-02): deleting an auth user fails with HTTP 500 as soon as the member has an
-- audit row (audit.actor -> auth.users has no ON DELETE action), and series_entitlements.user_id blocks it as well.
-- Goal: an admin can erase an ordinary member (withdrawal / deletion request) in one transaction without touching other members,
-- admins, the roster, lessons, materials or series codes. Admin and approver/issuer accounts are refused (organization owner handles those).
begin;

alter table classroom_private.audit alter column actor drop not null;
alter table classroom_private.audit drop constraint audit_actor_fkey;
alter table classroom_private.audit add constraint audit_actor_fkey foreign key (actor) references auth.users(id) on delete set null;

create function classroom_private.erase_member(p_user uuid) returns void
 language plpgsql security definer set search_path='' as $$
declare mail text;
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
 delete from classroom_private.series_entitlements where user_id=p_user;
 delete from classroom_private.code_attempts where user_id=p_user;
 update classroom_private.audit set target='erased' where target=p_user::text or (mail is not null and lower(target)=lower(mail));
 delete from auth.users where id=p_user; -- cascades profile, supporter request, auth sessions; audit.actor becomes null
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'member_erased','erased');
end $$;

create function public.somnium_erase_member(p_user uuid) returns void
 language sql security invoker set search_path='' as $$ select classroom_private.erase_member(p_user) $$;
revoke all on function public.somnium_erase_member(uuid) from public,anon;
grant execute on function public.somnium_erase_member(uuid) to authenticated;
revoke all on function classroom_private.erase_member(uuid) from public,anon;
grant execute on function classroom_private.erase_member(uuid) to authenticated;

commit;
