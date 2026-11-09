-- User 2026-11-09: administrators and explicitly assigned directors only.
begin;
create function classroom_private.can_view_reports() returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.is_admin() or (classroom_private.active() and exists(
 select 1 from classroom_private.directors d join auth.users u on lower(u.email)=d.email where u.id=auth.uid() and d.enabled))
$$;
revoke all on function classroom_private.can_view_reports() from public,anon;
grant execute on function classroom_private.can_view_reports() to authenticated;
create or replace function classroom_private.reports() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.can_view_reports() then raise exception 'director or admin required' using errcode='42501';end if;
 return(select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'period',period,'filename',filename,'path',storage_path,'enabled',enabled,'created_at',created_at) order by created_at desc),'[]'::jsonb) from classroom_private.accounting_reports where enabled or classroom_private.is_admin());
end$$;
create or replace function classroom_private.can_read_report(p_path text) returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.can_view_reports() and exists(select 1 from classroom_private.accounting_reports where storage_path=p_path and (enabled or classroom_private.is_admin()))
$$;
create or replace function public.somnium_me() returns jsonb language sql stable security invoker set search_path='' as $$
 select classroom_private.me() || jsonb_build_object('can_read_reports',classroom_private.can_view_reports())
$$;
commit;
