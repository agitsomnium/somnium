-- Shared seminar codes redeem an account-bound series entitlement. No payment.
begin;
create table classroom_private.series_products(
 key text primary key, title text not null, enabled boolean not null default true
);
create table classroom_private.series_lessons(
 product_key text references classroom_private.series_products(key),
 lesson_id uuid references classroom_private.lessons(id), primary key(product_key,lesson_id)
);
insert into classroom_private.series_products values('modern-capitalism-2026','현대자본주의 세미나 1',true);
insert into classroom_private.series_lessons
 select 'modern-capitalism-2026',id from classroom_private.lessons
 where era='current' and series_title='현대 자본주의 이해하기' and position between 1 and 6 and published;
do $$begin if (select count(*) from classroom_private.series_lessons)<>6 then raise exception 'Expected six seminar lessons';end if;end$$;
create table classroom_private.series_codes(
 id uuid primary key default gen_random_uuid(), product_key text not null references classroom_private.series_products(key),
 code_hash bytea not null unique, label text not null check(char_length(label) between 1 and 80),
 enabled boolean not null default true, issued_by uuid not null references auth.users(id), issued_at timestamptz not null default now()
);
create table classroom_private.series_entitlements(
 user_id uuid references auth.users(id), product_key text references classroom_private.series_products(key),
 code_id uuid not null references classroom_private.series_codes(id), enabled boolean not null default true,
 redeemed_at timestamptz not null default now(), primary key(user_id,product_key)
);
create table classroom_private.code_attempts(
 user_id uuid primary key references auth.users(id), window_at timestamptz not null, attempts integer not null
);
create table classroom_private.materials(
 id uuid primary key default gen_random_uuid(), lesson_id uuid references classroom_private.lessons(id),
 product_key text references classroom_private.series_products(key),
 title text not null check(char_length(title) between 1 and 200),
 filename text not null check(char_length(filename) between 1 and 220 and filename !~ '[/\\]'),
 storage_path text not null unique check(storage_path ~ '^[a-f0-9-]{36}[.]pdf$'),
 enabled boolean not null default true, created_at timestamptz not null default now(),
 check((lesson_id is null)<>(product_key is null))
);
create index series_lessons_lesson on classroom_private.series_lessons(lesson_id);
create index materials_lesson on classroom_private.materials(lesson_id);
create index materials_product on classroom_private.materials(product_key);
alter table classroom_private.series_products enable row level security;
alter table classroom_private.series_lessons enable row level security;
alter table classroom_private.series_codes enable row level security;
alter table classroom_private.series_entitlements enable row level security;
alter table classroom_private.code_attempts enable row level security;
alter table classroom_private.materials enable row level security;
revoke all on classroom_private.series_products,classroom_private.series_lessons,classroom_private.series_codes,classroom_private.series_entitlements,classroom_private.code_attempts,classroom_private.materials from public,anon,authenticated;

create function classroom_private.has_series(p_key text) returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.active() and exists(select 1 from classroom_private.series_entitlements e join classroom_private.series_products p on p.key=e.product_key
 where e.user_id=auth.uid() and e.product_key=p_key and e.enabled and p.enabled)
$$;
create function classroom_private.can_access_lesson(p_id uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from classroom_private.lessons l where l.id=p_id and l.published and
 (classroom_private.can_learn() or exists(select 1 from classroom_private.series_lessons s where s.lesson_id=l.id and classroom_private.has_series(s.product_key))))
$$;
create or replace function classroom_private.me() returns jsonb language sql stable security definer set search_path='' as $$
 select case when classroom_private.verified() then
 (select jsonb_build_object('id',p.id,'name',p.name,'suspended',p.suspended,'admin',classroom_private.is_admin(),
 'can_learn',classroom_private.can_learn() or exists(select 1 from classroom_private.series_entitlements e where e.user_id=p.id and classroom_private.has_series(e.product_key)),
 'full_access',classroom_private.can_learn(),'supporter_state',coalesce(s.state,'not_requested'))
 from classroom_private.profiles p left join classroom_private.supporters s on s.user_id=p.id where p.id=auth.uid()) else null end
$$;
create or replace function classroom_private.catalog() returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'description',description,'series_title',series_title,
 'position',position,'era',era,'thumbnail_url',case when provider='youtube' then 'https://i.ytimg.com/vi/'||video_id||'/mqdefault.jpg' else null end)
 order by series_title,position,id),'[]'::jsonb) from classroom_private.lessons where classroom_private.can_access_lesson(id)
$$;
create or replace function classroom_private.resource(p_id uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.can_access_lesson(p_id) then raise exception 'lecture access denied' using errcode='42501';end if;
 return (select jsonb_build_object('provider',provider,'video_id',video_id,'video_privacy',video_privacy,'material_path',material_path,'thumbnail_path',thumbnail_path)
 from classroom_private.lessons where id=p_id and published);
end$$;
create function classroom_private.issue_code(p_label text) returns jsonb language plpgsql security definer set search_path='' as $$
declare raw text;result uuid;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 raw:='SOM1-'||upper(replace(gen_random_uuid()::text,'-',''));
 insert into classroom_private.series_codes(product_key,code_hash,label,issued_by)
 values('modern-capitalism-2026',sha256(convert_to(replace(raw,'-',''),'UTF8')),btrim(p_label),auth.uid()) returning id into result;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'series_code_issued',result::text);
 return jsonb_build_object('id',result,'code',raw);
end$$;
create function classroom_private.redeem_code(p_code text) returns jsonb language plpgsql security definer set search_path='' as $$
declare c classroom_private.series_codes; n integer;ok boolean;
begin
 if not classroom_private.active() then raise exception 'active verified member required' using errcode='42501';end if;
 insert into classroom_private.code_attempts values(auth.uid(),now(),1)
 on conflict(user_id) do update set attempts=case when classroom_private.code_attempts.window_at<now()-interval '1 minute' then 1 else classroom_private.code_attempts.attempts+1 end,
 window_at=case when classroom_private.code_attempts.window_at<now()-interval '1 minute' then now() else classroom_private.code_attempts.window_at end returning attempts into n;
 if n>10 then return jsonb_build_object('ok',false,'reason','wait');end if;
 if p_code is null or char_length(p_code)>100 then return jsonb_build_object('ok',false,'reason','unavailable');end if;
 select * into c from classroom_private.series_codes where code_hash=sha256(convert_to(regexp_replace(upper(btrim(p_code)),'[ -]','','g'),'UTF8')) and enabled for update;
 if c.id is null or not exists(select 1 from classroom_private.series_products where key=c.product_key and enabled) then return jsonb_build_object('ok',false,'reason','unavailable');end if;
 insert into classroom_private.series_entitlements(user_id,product_key,code_id) values(auth.uid(),c.product_key,c.id) on conflict do nothing;
 select enabled into ok from classroom_private.series_entitlements where user_id=auth.uid() and product_key=c.product_key;
 if not ok then return jsonb_build_object('ok',false,'reason','unavailable');end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'series_code_redeemed',c.product_key);
 return jsonb_build_object('ok',true,'title',(select title from classroom_private.series_products where key=c.product_key));
end$$;
create function classroom_private.admin_series() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 return jsonb_build_object('codes',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'label',c.label,'enabled',c.enabled,'issued_at',c.issued_at,
 'registrations',(select count(*) from classroom_private.series_entitlements e where e.code_id=c.id)) order by c.issued_at desc),'[]'::jsonb) from classroom_private.series_codes c),
 'entitlements',(select coalesce(jsonb_agg(jsonb_build_object('user_id',e.user_id,'email',u.email,'product_key',e.product_key,'enabled',e.enabled)),'[]'::jsonb)
 from classroom_private.series_entitlements e join auth.users u on u.id=e.user_id));
end$$;
create function classroom_private.set_code(p_id uuid,p_enabled boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 update classroom_private.series_codes set enabled=p_enabled where id=p_id;
 if not found then raise exception 'code unavailable' using errcode='22023';end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'series_code_updated',p_id::text);
end$$;
create function classroom_private.set_entitlement(p_user uuid,p_enabled boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 update classroom_private.series_entitlements set enabled=p_enabled where user_id=p_user and product_key='modern-capitalism-2026';
 if not found then raise exception 'entitlement unavailable' using errcode='22023';end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'series_entitlement_updated',p_user::text);
end$$;
create function classroom_private.can_read_material(p_path text) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from classroom_private.materials m where m.storage_path=p_path and m.enabled and
 ((m.lesson_id is not null and classroom_private.can_access_lesson(m.lesson_id)) or
 (m.product_key is not null and (classroom_private.can_learn() or classroom_private.has_series(m.product_key)))))
$$;
create function classroom_private.materials(p_lesson uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.can_access_lesson(p_lesson) then raise exception 'lecture access denied' using errcode='42501';end if;
 return(select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'title',m.title,'filename',m.filename,'storage_path',m.storage_path,'kind',case when m.lesson_id is null then 'extra' else 'lesson' end) order by m.title),'[]'::jsonb)
 from classroom_private.materials m where m.enabled and (m.lesson_id=p_lesson or m.product_key in(select product_key from classroom_private.series_lessons where lesson_id=p_lesson)));
end$$;
create function classroom_private.save_material(p_lesson uuid,p_title text,p_filename text,p_path text) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 if not exists(select 1 from storage.objects where bucket_id='somnium-materials' and name=p_path) then raise exception 'upload first' using errcode='22023';end if;
 insert into classroom_private.materials(lesson_id,product_key,title,filename,storage_path)
 values(p_lesson,case when p_lesson is null then 'modern-capitalism-2026' else null end,btrim(p_title),p_filename,p_path) returning id into result;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'material_registered',result::text);
 return result;
end$$;
create function classroom_private.admin_materials() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 return(select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'filename',filename,'lesson_id',lesson_id,'enabled',enabled) order by created_at desc),'[]'::jsonb) from classroom_private.materials);
end$$;
create function classroom_private.set_material(p_id uuid,p_enabled boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 update classroom_private.materials set enabled=p_enabled where id=p_id;
 if not found then raise exception 'material unavailable' using errcode='22023';end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'material_visibility_updated',p_id::text);
end$$;
-- Only checked endpoints and the two policy helpers are executable by authenticated users.
revoke all on function classroom_private.has_series(text),classroom_private.can_access_lesson(uuid),classroom_private.issue_code(text),classroom_private.redeem_code(text),classroom_private.admin_series(),classroom_private.set_code(uuid,boolean),classroom_private.set_entitlement(uuid,boolean),classroom_private.can_read_material(text),classroom_private.materials(uuid),classroom_private.save_material(uuid,text,text,text),classroom_private.admin_materials(),classroom_private.set_material(uuid,boolean) from public,anon,authenticated;
grant execute on function classroom_private.issue_code(text),classroom_private.redeem_code(text),classroom_private.admin_series(),classroom_private.set_code(uuid,boolean),classroom_private.set_entitlement(uuid,boolean),classroom_private.can_read_material(text),classroom_private.materials(uuid),classroom_private.save_material(uuid,text,text,text),classroom_private.admin_materials(),classroom_private.set_material(uuid,boolean),classroom_private.is_admin() to authenticated;
create function public.somnium_issue_code(p_label text) returns jsonb language sql security invoker set search_path='' as $$select classroom_private.issue_code(p_label)$$;
create function public.somnium_redeem_code(p_code text) returns jsonb language sql security invoker set search_path='' as $$select classroom_private.redeem_code(p_code)$$;
create function public.somnium_admin_series() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.admin_series()$$;
create function public.somnium_set_code(p_id uuid,p_enabled boolean) returns void language sql security invoker set search_path='' as $$select classroom_private.set_code(p_id,p_enabled)$$;
create function public.somnium_set_entitlement(p_user uuid,p_enabled boolean) returns void language sql security invoker set search_path='' as $$select classroom_private.set_entitlement(p_user,p_enabled)$$;
create function public.somnium_materials(p_lesson uuid) returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.materials(p_lesson)$$;
create function public.somnium_save_material(p_lesson uuid,p_title text,p_filename text,p_path text) returns uuid language sql security invoker set search_path='' as $$select classroom_private.save_material(p_lesson,p_title,p_filename,p_path)$$;
create function public.somnium_admin_materials() returns jsonb language sql stable security invoker set search_path='' as $$select classroom_private.admin_materials()$$;
create function public.somnium_set_material(p_id uuid,p_enabled boolean) returns void language sql security invoker set search_path='' as $$select classroom_private.set_material(p_id,p_enabled)$$;
revoke all on function public.somnium_issue_code(text),public.somnium_redeem_code(text),public.somnium_admin_series(),public.somnium_set_code(uuid,boolean),public.somnium_set_entitlement(uuid,boolean),public.somnium_materials(uuid),public.somnium_save_material(uuid,text,text,text),public.somnium_admin_materials(),public.somnium_set_material(uuid,boolean) from public,anon;
grant execute on function public.somnium_issue_code(text),public.somnium_redeem_code(text),public.somnium_admin_series(),public.somnium_set_code(uuid,boolean),public.somnium_set_entitlement(uuid,boolean),public.somnium_materials(uuid),public.somnium_save_material(uuid,text,text,text),public.somnium_admin_materials(),public.somnium_set_material(uuid,boolean) to authenticated;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('somnium-materials','somnium-materials',false,26214400,array['application/pdf']);
create policy somnium_material_read on storage.objects for select to authenticated using(bucket_id='somnium-materials' and classroom_private.can_read_material(name));
create policy somnium_material_upload on storage.objects for insert to authenticated with check(bucket_id='somnium-materials' and name ~ '^[a-f0-9-]{36}[.]pdf$' and classroom_private.is_admin());
commit;
