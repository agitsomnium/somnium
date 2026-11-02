-- DRAFT · NOT APPLIED. Undo of 20261102_member_erasure_DRAFT.sql.
-- Safe only while no member has been erased. The test is the ledger (one row per erasure, also for members who had no audit rows of their own),
-- with the audit checks kept as a second guard. Erased personal data itself is never restored by this script.
-- Erased personal data itself is never restored by this script (only a backup + the deletion ledger can do that).
begin;
do $$ begin
 if exists(select 1 from classroom_private.erasure_ledger)
  or exists(select 1 from classroom_private.audit where action='member_erased' or actor is null) then
  raise exception 'rollback refused: an erasure has been executed (keep the ledger, the nullable audit.actor and the functions)' using errcode='55000';
 end if;
end $$;
drop function classroom_private.erasure_ledger_pending();
drop function classroom_private.apply_erasure_ledger();
drop function classroom_private.import_erasure_ledger(jsonb);
drop function classroom_private.export_erasure_ledger();
drop function public.somnium_erase_member(uuid);
drop function classroom_private.erase_member(uuid);
drop function classroom_private.erasure_hash(text);
drop table classroom_private.erasure_ledger;
alter table classroom_private.audit drop constraint audit_actor_fkey;
alter table classroom_private.audit add constraint audit_actor_fkey foreign key (actor) references auth.users(id);
alter table classroom_private.audit alter column actor set not null;
commit;
