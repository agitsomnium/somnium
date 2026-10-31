-- Existing Somnium private schema only. No new roles or direct table grants.
begin;
create function classroom_private.admin_lessons() returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(to_jsonb(l) order by l.series_title,l.position,l.id),'[]'::jsonb) from classroom_private.lessons l);
end $$;
create function classroom_private.admin_directors() returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('email',email,'enabled',enabled) order by email),'[]'::jsonb) from classroom_private.directors);
end $$;
create function classroom_private.admin_audit() returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(to_jsonb(a) order by a.id desc),'[]'::jsonb) from (select id,at,action,target from classroom_private.audit order by id desc limit 50) a);
end $$;
revoke all on function classroom_private.admin_lessons(),classroom_private.admin_directors(),classroom_private.admin_audit() from public,anon,authenticated;
grant execute on function classroom_private.admin_lessons(),classroom_private.admin_directors(),classroom_private.admin_audit() to authenticated;
create function public.somnium_admin_lessons() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.admin_lessons()$$;
create function public.somnium_admin_directors() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.admin_directors()$$;
create function public.somnium_admin_audit() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.admin_audit()$$;
revoke all on function public.somnium_admin_lessons(),public.somnium_admin_directors(),public.somnium_admin_audit() from public,anon;
grant execute on function public.somnium_admin_lessons(),public.somnium_admin_directors(),public.somnium_admin_audit() to authenticated;
commit;
