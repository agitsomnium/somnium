-- DRAFT · NOT APPLIED. Undo of 20261102_member_erasure_DRAFT.sql.
-- Safe only while no member has been erased: erased members leave audit.actor = NULL, and NOT NULL cannot be restored over them.
-- Erased personal data itself is never restored by this script (only a backup + the deletion ledger can do that).
begin;
do $$ begin
 if exists(select 1 from classroom_private.audit where actor is null) then
  raise exception 'rollback refused: audit rows with erased actors exist (keep audit.actor nullable)' using errcode='55000';
 end if;
end $$;
drop function public.somnium_erase_member(uuid);
drop function classroom_private.erase_member(uuid);
alter table classroom_private.audit drop constraint audit_actor_fkey;
alter table classroom_private.audit add constraint audit_actor_fkey foreign key (actor) references auth.users(id);
alter table classroom_private.audit alter column actor set not null;
commit;
