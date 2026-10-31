-- The dashboard's automatic-RLS option creates an event-trigger helper in public.
-- Keep the trigger, remove unnecessary direct execution by API clients.
begin;
do $$
begin
 if to_regprocedure('public.rls_auto_enable()') is not null then
  revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
 end if;
end $$;
commit;
