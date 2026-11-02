begin;
create table classroom_private.accounting_reports(
 id uuid primary key default gen_random_uuid(),
 title text not null check(char_length(title) between 1 and 160),
 period text not null default '' check(char_length(period)<=80),
 filename text not null check(char_length(filename) between 1 and 220 and filename !~ '[/\\]' and filename ~* '[.]pdf$'),
 storage_path text not null unique check(storage_path ~ '^[a-f0-9-]{36}[.]pdf$'),
 enabled boolean not null default true,
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now()
);
alter table classroom_private.accounting_reports enable row level security;
revoke all on classroom_private.accounting_reports from public,anon,authenticated;

create function classroom_private.reports() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.active() then raise exception 'active registered member required' using errcode='42501';end if;
 return(select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'period',period,'filename',filename,'path',storage_path,'enabled',enabled,'created_at',created_at) order by created_at desc),'[]'::jsonb)
 from classroom_private.accounting_reports where enabled or classroom_private.is_admin());
end$$;
create function classroom_private.can_read_report(p_path text) returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.active() and exists(select 1 from classroom_private.accounting_reports where storage_path=p_path and (enabled or classroom_private.is_admin()))
$$;
create function classroom_private.save_report(p_title text,p_period text,p_filename text,p_path text,p_enabled boolean default true) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 if not exists(select 1 from storage.objects where bucket_id='somnium-accounting' and name=p_path and metadata->>'mimetype'='application/pdf' and (metadata->>'size')::bigint between 1 and 26214400) then raise exception 'uploaded PDF required' using errcode='22023';end if;
 insert into classroom_private.accounting_reports(title,period,filename,storage_path,created_by,enabled) values(btrim(p_title),btrim(coalesce(p_period,'')),p_filename,p_path,auth.uid(),p_enabled) returning id into result;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'accounting_report_added',result::text);
 return result;
end$$;
create function classroom_private.set_report(p_id uuid,p_enabled boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 if p_enabled is null then raise exception 'enabled value required' using errcode='22023';end if;
 update classroom_private.accounting_reports set enabled=p_enabled where id=p_id;
 if not found then raise exception 'report missing' using errcode='22023';end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),case when p_enabled then 'accounting_report_shown' else 'accounting_report_hidden' end,p_id::text);
end$$;
revoke all on function classroom_private.reports(),classroom_private.can_read_report(text),classroom_private.save_report(text,text,text,text,boolean),classroom_private.set_report(uuid,boolean) from public,anon,authenticated;
grant execute on function classroom_private.reports(),classroom_private.can_read_report(text),classroom_private.save_report(text,text,text,text,boolean),classroom_private.set_report(uuid,boolean) to authenticated;
create function public.somnium_reports() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.reports()$$;
create function public.somnium_save_report(p_title text,p_period text,p_filename text,p_path text,p_enabled boolean default true) returns uuid language sql security invoker set search_path='' as $$select classroom_private.save_report(p_title,p_period,p_filename,p_path,p_enabled)$$;
create function public.somnium_set_report(p_id uuid,p_enabled boolean) returns void language sql security invoker set search_path='' as $$select classroom_private.set_report(p_id,p_enabled)$$;
revoke all on function public.somnium_reports(),public.somnium_save_report(text,text,text,text,boolean),public.somnium_set_report(uuid,boolean) from public,anon;
grant execute on function public.somnium_reports(),public.somnium_save_report(text,text,text,text,boolean),public.somnium_set_report(uuid,boolean) to authenticated;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('somnium-accounting','somnium-accounting',false,26214400,array['application/pdf']);
create policy somnium_accounting_read on storage.objects for select to authenticated using(bucket_id='somnium-accounting' and classroom_private.can_read_report(name));
create policy somnium_accounting_upload on storage.objects for insert to authenticated with check(bucket_id='somnium-accounting' and name ~ '^[a-f0-9-]{36}[.]pdf$' and classroom_private.is_admin());
commit;
