begin;
create extension if not exists pg_net with schema extensions;
alter table classroom_private.supporters add column access_basis text not null default 'payment_checked'
 check(access_basis in ('payment_checked','self_declared'));
alter table classroom_private.supporters drop constraint supporters_check;
alter table classroom_private.supporters add constraint supporters_check
 check(state <> 'qualified' or access_basis='self_declared' or (checked_at is not null and checked_by is not null));
create table classroom_private.supporter_notices (
 user_id uuid primary key references auth.users(id) on delete cascade,
 created_at timestamptz not null default now(),
 attempted_at timestamptz, sent_at timestamptz,
 state text not null default 'pending' check(state in ('pending','sending','sent'))
);
alter table classroom_private.supporter_notices enable row level security;
revoke all on classroom_private.supporter_notices from public,anon,authenticated;

-- Qualification grants lecture access; a null checked_at means monthly payment reconciliation is still due.
create or replace function classroom_private.request_supporter() returns void
language plpgsql security definer set search_path='' as $$
declare previous text; changed integer; bearer text;
begin
 if not classroom_private.active() then raise exception 'active verified membership required' using errcode='42501'; end if;
 select state into previous from classroom_private.supporters where user_id=auth.uid() for update;
 if previous in ('held','withdrawn') then raise exception '문의 메일로 후원 자격 재개를 요청해 주세요.' using errcode='42501'; end if;
 insert into classroom_private.supporters(user_id,state,checked_at,checked_by,access_basis)
 values(auth.uid(),'qualified',null,null,'self_declared')
 on conflict(user_id) do update set state='qualified',checked_at=null,checked_by=null,access_basis='self_declared'
 where classroom_private.supporters.state='pending';
 get diagnostics changed = row_count;
 if changed > 0 then
  insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_self_declared',auth.uid()::text);
  insert into classroom_private.supporter_notices(user_id) values(auth.uid()) on conflict do nothing;
 end if;
 -- Queue notification independently of browser lifetime. Its failure never cancels lecture access.
 bearer := current_setting('request.headers',true)::jsonb->>'authorization';
 if bearer is not null and exists(select 1 from classroom_private.supporter_notices where user_id=auth.uid() and sent_at is null) then
  begin
   perform net.http_post(url:='https://jdfrottxrdhglxtqvtyx.supabase.co/functions/v1/supporter-notice',
    headers:=jsonb_build_object('Content-Type','application/json','Authorization',bearer),body:='{}'::jsonb,timeout_milliseconds:=15000);
  exception when others then null;
  end;
 end if;
end $$;

create or replace function classroom_private.review_supporter(p_user uuid,p_state text,p_minimum_confirmed boolean) returns void
language plpgsql security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_state not in ('qualified','held','withdrawn') or p_state is null or (p_state='qualified' and p_minimum_confirmed is distinct from true) then raise exception 'manual minimum donation check required' using errcode='22023'; end if;
 if not exists(select 1 from classroom_private.profiles p join auth.users u on p.id=u.id where p.id=p_user and u.email_confirmed_at is not null) then raise exception 'verified profile required' using errcode='22023'; end if;
 insert into classroom_private.supporters(user_id,state,checked_at,checked_by,access_basis) values(p_user,p_state,now(),auth.uid(),'payment_checked')
 on conflict(user_id) do update set state=excluded.state,checked_at=excluded.checked_at,checked_by=excluded.checked_by,access_basis=excluded.access_basis;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_'||p_state,p_user::text);
end $$;

create function classroom_private.claim_supporter_notice(p_user uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare claimed uuid;
begin
 update classroom_private.supporter_notices set state='sending',attempted_at=now()
 where user_id=p_user and sent_at is null and (attempted_at is null or attempted_at<now()-interval '1 minute')
 returning user_id into claimed;
 if claimed is null then return null; end if;
 return (select jsonb_build_object('user_id',p.id,'name',p.name,'email',u.email,'created_at',n.created_at)
 from classroom_private.profiles p join auth.users u on u.id=p.id join classroom_private.supporter_notices n on n.user_id=p.id where p.id=claimed);
end $$;
create function classroom_private.finish_supporter_notice(p_user uuid,p_sent boolean) returns void
language sql security definer set search_path='' as $$
 update classroom_private.supporter_notices set state=case when p_sent then 'sent' else 'pending' end,
 sent_at=case when p_sent then now() else null end where user_id=p_user and sent_at is null
$$;
revoke all on function classroom_private.claim_supporter_notice(uuid),classroom_private.finish_supporter_notice(uuid,boolean) from public,anon,authenticated;
grant usage on schema classroom_private to service_role;
grant execute on function classroom_private.claim_supporter_notice(uuid),classroom_private.finish_supporter_notice(uuid,boolean) to service_role;
create function public.somnium_claim_supporter_notice(p_user uuid) returns jsonb
language sql security invoker set search_path='' as $$select classroom_private.claim_supporter_notice(p_user)$$;
create function public.somnium_finish_supporter_notice(p_user uuid,p_sent boolean) returns void
language sql security invoker set search_path='' as $$select classroom_private.finish_supporter_notice(p_user,p_sent)$$;
revoke all on function public.somnium_claim_supporter_notice(uuid),public.somnium_finish_supporter_notice(uuid,boolean) from public,anon,authenticated;
grant execute on function public.somnium_claim_supporter_notice(uuid),public.somnium_finish_supporter_notice(uuid,boolean) to service_role;

create or replace function classroom_private.admin_members() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'birth',p.birth,'phone',p.phone,
 'email',u.email,'supporter_name',p.supporter_name,'suspended',p.suspended,'supporter_state',coalesce(s.state,'not_requested'),
 'access_basis',s.access_basis,'checked_at',s.checked_at,'requested_at',s.requested_at,'notice_state',n.state,'notice_sent_at',n.sent_at)
 order by p.name),'[]'::jsonb)
 from classroom_private.profiles p join auth.users u on p.id=u.id left join classroom_private.supporters s on s.user_id=p.id
 left join classroom_private.supporter_notices n on n.user_id=p.id);
end $$;
notify pgrst,'reload schema';
commit;
