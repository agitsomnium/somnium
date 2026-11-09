-- User 2026-11-09: keep accounting private until its audience is decided.
begin;
create or replace function classroom_private.reports() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 return(select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'period',period,'filename',filename,'path',storage_path,'enabled',enabled,'created_at',created_at) order by created_at desc),'[]'::jsonb) from classroom_private.accounting_reports);
end$$;
create or replace function classroom_private.can_read_report(p_path text) returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.is_admin() and exists(select 1 from classroom_private.accounting_reports where storage_path=p_path)
$$;
commit;
