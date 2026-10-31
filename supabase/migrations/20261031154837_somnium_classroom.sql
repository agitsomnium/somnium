-- Apply ONLY to a new organization-owned Somnium project, never the personal Hub.
-- Tables and elevated functions stay outside exposed schemas. Public RPCs are invokers.
begin;
create schema classroom_private;
revoke all on schema classroom_private from public;
grant usage on schema classroom_private to authenticated;

create table classroom_private.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 name text not null check (char_length(name) between 2 and 40),
 birth date not null check (birth >= date '1900-01-01' and birth <= current_date),
 phone text not null check (phone ~ '^01[0-9]{8,9}$'),
 consent_version text not null, consent_at timestamptz not null default now(),
 suspended boolean not null default false
);
create table classroom_private.admins (
 user_id uuid primary key references auth.users(id) on delete cascade,
 enabled boolean not null default true
);
create table classroom_private.supporters (
 user_id uuid primary key references auth.users(id) on delete cascade,
 state text not null check (state in ('pending','qualified','held','withdrawn')),
 requested_at timestamptz not null default now(), checked_at timestamptz,
 checked_by uuid references auth.users(id),
 check (state <> 'qualified' or (checked_at is not null and checked_by is not null))
);
create table classroom_private.directors (
 email text primary key check (email=lower(btrim(email)) and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
 enabled boolean not null, checked_at timestamptz not null default now(),
 checked_by uuid not null references auth.users(id)
);
create table classroom_private.lessons (
 id uuid primary key default gen_random_uuid(), title text not null check (char_length(title) between 1 and 100),
 description text not null default '' check (char_length(description)<=1200),
 series_title text not null default '' check (char_length(series_title)<=100),
 position integer not null default 1 check (position between 1 and 999),
 era text not null check (era in ('archive','current','future')),
 published boolean not null default false,
 provider text not null check (provider in ('youtube','vimeo')),
 video_id text not null, video_privacy text not null default '',
 material_path text, thumbnail_path text,
 check ((provider='youtube' and video_id ~ '^[A-Za-z0-9_-]{11}$' and video_privacy='') or
        (provider='vimeo' and video_id ~ '^[0-9]{6,12}$' and (video_privacy='' or video_privacy ~ '^[A-Za-z0-9]{6,32}$'))),
 check (material_path is null or (material_path ~ '^[A-Za-z0-9_/-]+\.(pdf|txt)$' and material_path !~ '\.\.' )),
 check (thumbnail_path is null or (thumbnail_path ~ '^[A-Za-z0-9_/-]+\.(png|jpg|webp)$' and thumbnail_path !~ '\.\.' ))
);
create table classroom_private.audit (
 id bigint generated always as identity primary key, at timestamptz not null default now(),
 actor uuid not null references auth.users(id), action text not null, target text not null
);
alter table classroom_private.profiles enable row level security;
alter table classroom_private.admins enable row level security;
alter table classroom_private.supporters enable row level security;
alter table classroom_private.directors enable row level security;
alter table classroom_private.lessons enable row level security;
alter table classroom_private.audit enable row level security;
-- No direct table access or permissive policies. All access goes through checked RPCs.
revoke all on all tables in schema classroom_private from public,anon,authenticated;
revoke all on all sequences in schema classroom_private from public,anon,authenticated;

create function classroom_private.verified() returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from auth.users u where u.id=(select auth.uid()) and u.email_confirmed_at is not null)
$$;
create function classroom_private.active() returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.verified() and exists(select 1 from classroom_private.profiles p where p.id=(select auth.uid()) and not p.suspended)
$$;
create function classroom_private.is_admin() returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.active() and exists(select 1 from classroom_private.admins a where a.user_id=(select auth.uid()) and a.enabled)
$$;
create function classroom_private.can_learn() returns boolean language sql stable security definer set search_path='' as $$
 select classroom_private.active() and (classroom_private.is_admin() or
 exists(select 1 from classroom_private.supporters s where s.user_id=(select auth.uid()) and s.state='qualified') or
 exists(select 1 from classroom_private.directors d join auth.users u on lower(u.email)=d.email where u.id=(select auth.uid()) and d.enabled))
$$;
create function classroom_private.complete_profile(p_name text,p_birth date,p_phone text,p_consent boolean) returns void
 language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.verified() then raise exception 'email verification required' using errcode='42501'; end if;
 if p_consent is distinct from true then raise exception 'consent required' using errcode='22023'; end if;
 insert into classroom_private.profiles(id,name,birth,phone,consent_version)
 values(auth.uid(),btrim(p_name),p_birth,p_phone,'somnium-v1-draft')
 on conflict(id) do update set name=excluded.name,birth=excluded.birth,phone=excluded.phone;
 -- Existing suspension and consent history cannot be reset by re-registering.
end $$;
create function classroom_private.me() returns jsonb language sql stable security definer set search_path='' as $$
 select case when classroom_private.verified() then
 (select jsonb_build_object('id',p.id,'name',p.name,'suspended',p.suspended,'admin',classroom_private.is_admin(),
 'can_learn',classroom_private.can_learn(),'supporter_state',coalesce(s.state,'not_requested'))
 from classroom_private.profiles p left join classroom_private.supporters s on s.user_id=p.id where p.id=auth.uid()) else null end
$$;
create function classroom_private.request_supporter() returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.active() then raise exception 'active verified membership required' using errcode='42501'; end if;
 insert into classroom_private.supporters(user_id,state) values(auth.uid(),'pending')
 on conflict(user_id) do update set state='pending',requested_at=now(),checked_at=null,checked_by=null
 where classroom_private.supporters.state in ('held','withdrawn');
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_requested',auth.uid()::text);
end $$;
create function classroom_private.catalog() returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title,'description',description,'series_title',series_title,
 'position',position,'era',era) order by series_title,position,id),'[]'::jsonb)
 from classroom_private.lessons where published and classroom_private.can_learn()
$$;
create function classroom_private.resource(p_id uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if not classroom_private.can_learn() then raise exception 'lecture access denied' using errcode='42501'; end if;
 select jsonb_build_object('provider',provider,'video_id',video_id,'video_privacy',video_privacy,
 'material_path',material_path,'thumbnail_path',thumbnail_path) into result
 from classroom_private.lessons where id=p_id and published;
 if result is null then raise exception 'lecture unavailable' using errcode='42501'; end if;
 return result;
end $$;
create function classroom_private.admin_members() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'birth',p.birth,'phone',p.phone,
 'email',u.email,'suspended',p.suspended,'supporter_state',coalesce(s.state,'not_requested')) order by p.name),'[]'::jsonb)
 from classroom_private.profiles p join auth.users u on p.id=u.id left join classroom_private.supporters s on s.user_id=p.id);
end $$;
create function classroom_private.review_supporter(p_user uuid,p_state text,p_minimum_confirmed boolean) returns void
 language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_state not in ('qualified','held','withdrawn') or p_state is null or (p_state='qualified' and p_minimum_confirmed is distinct from true) then raise exception 'manual minimum donation check required' using errcode='22023'; end if;
 if not exists(select 1 from classroom_private.profiles p join auth.users u on p.id=u.id where p.id=p_user and u.email_confirmed_at is not null) then raise exception 'verified profile required' using errcode='22023'; end if;
 insert into classroom_private.supporters(user_id,state,checked_at,checked_by) values(p_user,p_state,now(),auth.uid())
 on conflict(user_id) do update set state=excluded.state,checked_at=excluded.checked_at,checked_by=excluded.checked_by;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_'||p_state,p_user::text);
end $$;
create function classroom_private.set_director(p_email text,p_enabled boolean,p_roster_confirmed boolean) returns void
 language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_enabled is null or (p_enabled and p_roster_confirmed is distinct from true) then raise exception 'internal roster check required' using errcode='22023'; end if;
 insert into classroom_private.directors(email,enabled,checked_by) values(lower(btrim(p_email)),p_enabled,auth.uid())
 on conflict(email) do update set enabled=excluded.enabled,checked_at=now(),checked_by=excluded.checked_by;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'director_updated',lower(btrim(p_email)));
end $$;
create function classroom_private.suspend_member(p_user uuid,p_suspended boolean) returns void
 language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_user=auth.uid() or p_suspended is null or exists(select 1 from classroom_private.admins where user_id=p_user and enabled) then raise exception 'admin access changes require organization owner' using errcode='22023'; end if;
 update classroom_private.profiles set suspended=p_suspended where id=p_user;
 if not found then raise exception 'member unavailable' using errcode='22023'; end if;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'suspension_updated',p_user::text);
end $$;
create function classroom_private.save_lesson(p_id uuid,p_title text,p_description text,p_series text,p_position integer,p_era text,p_published boolean,p_provider text,p_video_id text,p_video_privacy text) returns uuid
 language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 insert into classroom_private.lessons(id,title,description,series_title,position,era,published,provider,video_id,video_privacy)
 values(coalesce(p_id,gen_random_uuid()),p_title,p_description,p_series,p_position,p_era,p_published,p_provider,p_video_id,p_video_privacy)
 on conflict(id) do update set title=excluded.title,description=excluded.description,series_title=excluded.series_title,
 position=excluded.position,era=excluded.era,published=excluded.published,provider=excluded.provider,video_id=excluded.video_id,video_privacy=excluded.video_privacy returning id into result;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'lesson_saved',result::text);
 return result;
end $$;
-- Deny default PUBLIC function execution, including helpers. Invoker wrappers below
-- explicitly expose only named, authenticated entry points. Private schema stays unexposed.
revoke all on all functions in schema classroom_private from public,anon,authenticated;
grant execute on function classroom_private.complete_profile(text,date,text,boolean),classroom_private.me(),classroom_private.request_supporter(),classroom_private.catalog(),classroom_private.resource(uuid),classroom_private.admin_members(),classroom_private.review_supporter(uuid,text,boolean),classroom_private.set_director(text,boolean,boolean),classroom_private.suspend_member(uuid,boolean),classroom_private.save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text) to authenticated;

create function public.somnium_complete_profile(p_name text,p_birth date,p_phone text,p_consent boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.complete_profile(p_name,p_birth,p_phone,p_consent) $$;
create function public.somnium_me() returns jsonb language sql stable security invoker set search_path='' as $$ select classroom_private.me() $$;
create function public.somnium_request_supporter() returns void language sql security invoker set search_path='' as $$ select classroom_private.request_supporter() $$;
create function public.somnium_catalog() returns jsonb language sql stable security invoker set search_path='' as $$ select classroom_private.catalog() $$;
create function public.somnium_resource(p_id uuid) returns jsonb language sql stable security invoker set search_path='' as $$ select classroom_private.resource(p_id) $$;
create function public.somnium_admin_members() returns jsonb language sql stable security invoker set search_path='' as $$ select classroom_private.admin_members() $$;
create function public.somnium_review_supporter(p_user uuid,p_state text,p_minimum_confirmed boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.review_supporter(p_user,p_state,p_minimum_confirmed) $$;
create function public.somnium_set_director(p_email text,p_enabled boolean,p_roster_confirmed boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.set_director(p_email,p_enabled,p_roster_confirmed) $$;
create function public.somnium_suspend_member(p_user uuid,p_suspended boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.suspend_member(p_user,p_suspended) $$;
create function public.somnium_save_lesson(p_id uuid,p_title text,p_description text,p_series text,p_position integer,p_era text,p_published boolean,p_provider text,p_video_id text,p_video_privacy text) returns uuid language sql security invoker set search_path='' as $$ select classroom_private.save_lesson(p_id,p_title,p_description,p_series,p_position,p_era,p_published,p_provider,p_video_id,p_video_privacy) $$;
-- Do not revoke unrelated public functions in an existing project.
revoke all on function public.somnium_complete_profile(text,date,text,boolean),public.somnium_me(),public.somnium_request_supporter(),public.somnium_catalog(),public.somnium_resource(uuid),public.somnium_admin_members(),public.somnium_review_supporter(uuid,text,boolean),public.somnium_set_director(text,boolean,boolean),public.somnium_suspend_member(uuid,boolean),public.somnium_save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text) from public,anon;
grant execute on function public.somnium_complete_profile(text,date,text,boolean),public.somnium_me(),public.somnium_request_supporter(),public.somnium_catalog(),public.somnium_resource(uuid),public.somnium_admin_members(),public.somnium_review_supporter(uuid,text,boolean),public.somnium_set_director(text,boolean,boolean),public.somnium_suspend_member(uuid,boolean),public.somnium_save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text) to authenticated;
commit;
