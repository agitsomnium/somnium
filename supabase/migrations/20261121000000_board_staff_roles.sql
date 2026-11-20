-- User 2026-11-21: 간사(staff)도 이사처럼 회계 보고를 본다. 로그인한 회원이 이사·간사 등록을 신청하고 관리자가 명단 확인 뒤 승인한다.
-- 보고서 등록·공개 전환은 계속 관리자만. directors 표에 있는 enabled 행이면 role과 무관하게 can_view_reports·can_learn 통과(기존 함수 그대로).
begin;
alter table classroom_private.directors add column role text not null default 'director' check (role in ('director','staff'));
create table classroom_private.role_requests (
 user_id uuid primary key references auth.users(id) on delete cascade,
 role text not null check (role in ('director','staff')),
 state text not null default 'pending' check (state in ('pending','approved','declined')),
 requested_at timestamptz not null default now(), checked_at timestamptz,
 checked_by uuid references auth.users(id),
 check (state='pending' or (checked_at is not null and checked_by is not null))
);
alter table classroom_private.role_requests enable row level security;
revoke all on table classroom_private.role_requests from public,anon,authenticated;

create function classroom_private.my_role() returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object(
  'board_role',(select d.role from classroom_private.directors d join auth.users u on lower(u.email)=d.email where u.id=auth.uid() and d.enabled and classroom_private.active()),
  'role_request',(select jsonb_build_object('role',r.role,'state',r.state) from classroom_private.role_requests r where r.user_id=auth.uid()))
$$;
create function classroom_private.request_role(p_role text) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.active() then raise exception 'active verified membership required' using errcode='42501'; end if;
 if p_role is null or p_role not in ('director','staff') then raise exception 'role must be director or staff' using errcode='22023'; end if;
 if exists(select 1 from classroom_private.directors d join auth.users u on lower(u.email)=d.email where u.id=auth.uid() and d.enabled) then
  raise exception 'already registered' using errcode='22023'; end if;
 insert into classroom_private.role_requests(user_id,role) values(auth.uid(),p_role)
 on conflict(user_id) do update set role=excluded.role,state='pending',requested_at=now(),checked_at=null,checked_by=null;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'role_requested_'||p_role,auth.uid()::text);
end $$;
create function classroom_private.review_role_request(p_user uuid,p_approve boolean,p_roster_confirmed boolean) returns void language plpgsql security definer set search_path='' as $$
declare v_email text; v_role text;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_user is null or p_approve is null then raise exception 'user and decision required' using errcode='22023'; end if;
 if p_user=auth.uid() then raise exception 'self review not allowed' using errcode='42501'; end if;
 select r.role into v_role from classroom_private.role_requests r where r.user_id=p_user and r.state='pending' for update;
 if v_role is null then raise exception 'no pending request' using errcode='22023'; end if;
 if p_approve then
  if p_roster_confirmed is distinct from true then raise exception 'internal roster check required' using errcode='22023'; end if;
  select lower(btrim(u.email)) into v_email from auth.users u where u.id=p_user and u.email_confirmed_at is not null;
  if v_email is null then raise exception 'verified email required' using errcode='22023'; end if;
  insert into classroom_private.directors(email,enabled,checked_by,role) values(v_email,true,auth.uid(),v_role)
  on conflict(email) do update set enabled=true,role=excluded.role,checked_at=now(),checked_by=excluded.checked_by;
 end if;
 update classroom_private.role_requests set state=case when p_approve then 'approved' else 'declined' end,checked_at=now(),checked_by=auth.uid() where user_id=p_user;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),case when p_approve then 'role_approved_' else 'role_declined_' end||v_role,p_user::text);
end $$;
create function classroom_private.set_board_member(p_email text,p_role text,p_enabled boolean,p_roster_confirmed boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_role is null or p_role not in ('director','staff') then raise exception 'role must be director or staff' using errcode='22023'; end if;
 if p_enabled is null or (p_enabled and p_roster_confirmed is distinct from true) then raise exception 'internal roster check required' using errcode='22023'; end if;
 insert into classroom_private.directors(email,enabled,checked_by,role) values(lower(btrim(p_email)),p_enabled,auth.uid(),p_role)
 on conflict(email) do update set enabled=excluded.enabled,role=excluded.role,checked_at=now(),checked_by=excluded.checked_by;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),p_role||'_updated',lower(btrim(p_email)));
end $$;
create or replace function classroom_private.admin_directors() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('email',email,'enabled',enabled,'role',role) order by role,email),'[]'::jsonb) from classroom_private.directors);
end $$;
create function classroom_private.admin_role_requests() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('user_id',r.user_id,'role',r.role,'name',p.name,'email',u.email,'requested_at',r.requested_at) order by r.requested_at),'[]'::jsonb)
  from classroom_private.role_requests r join auth.users u on u.id=r.user_id left join classroom_private.profiles p on p.id=r.user_id where r.state='pending');
end $$;
revoke all on function classroom_private.my_role(),classroom_private.request_role(text),classroom_private.review_role_request(uuid,boolean,boolean),classroom_private.set_board_member(text,text,boolean,boolean),classroom_private.admin_role_requests() from public,anon,authenticated;
grant execute on function classroom_private.my_role(),classroom_private.request_role(text),classroom_private.review_role_request(uuid,boolean,boolean),classroom_private.set_board_member(text,text,boolean,boolean),classroom_private.admin_role_requests() to authenticated;

create or replace function public.somnium_me() returns jsonb language sql stable security invoker set search_path='' as $$
 select classroom_private.me() || jsonb_build_object('can_read_reports',classroom_private.can_view_reports()) || classroom_private.my_role()
$$;
create function public.somnium_request_role(p_role text) returns void language sql security invoker set search_path='' as $$ select classroom_private.request_role(p_role) $$;
create function public.somnium_review_role_request(p_user uuid,p_approve boolean,p_roster_confirmed boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.review_role_request(p_user,p_approve,p_roster_confirmed) $$;
create function public.somnium_set_board_member(p_email text,p_role text,p_enabled boolean,p_roster_confirmed boolean) returns void language sql security invoker set search_path='' as $$ select classroom_private.set_board_member(p_email,p_role,p_enabled,p_roster_confirmed) $$;
create function public.somnium_admin_role_requests() returns jsonb language sql stable security invoker set search_path='' as $$ select classroom_private.admin_role_requests() $$;
revoke all on function public.somnium_request_role(text),public.somnium_review_role_request(uuid,boolean,boolean),public.somnium_set_board_member(text,text,boolean,boolean),public.somnium_admin_role_requests() from public,anon;
grant execute on function public.somnium_request_role(text),public.somnium_review_role_request(uuid,boolean,boolean),public.somnium_set_board_member(text,text,boolean,boolean),public.somnium_admin_role_requests() to authenticated;
commit;
