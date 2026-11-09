-- 2026-11-09 user: new supporter requests require operator approval; payment reconciliation remains separate.
begin;
create or replace function classroom_private.request_supporter() returns void
language plpgsql security definer set search_path='' as $$
declare previous text; changed integer; bearer text;
begin
 if not classroom_private.active() then raise exception 'active verified membership required' using errcode='42501'; end if;
 select state into previous from classroom_private.supporters where user_id=auth.uid() for update;
 if previous in ('held','withdrawn') then raise exception '문의 메일로 후원 자격 재개를 요청해 주세요.' using errcode='42501'; end if;
 insert into classroom_private.supporters(user_id,state,checked_at,checked_by,access_basis)
 values(auth.uid(),'pending',null,null,'self_declared')
 on conflict(user_id) do nothing;
 get diagnostics changed = row_count;
 if changed > 0 then
  insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_approval_requested',auth.uid()::text);
  insert into classroom_private.supporter_notices(user_id) values(auth.uid()) on conflict do nothing;
 end if;
 -- Queue notification independently of browser lifetime. Delivery does not grant lecture access.
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
 if p_state not in ('qualified','held','withdrawn') or p_state is null then raise exception 'invalid supporter state' using errcode='22023'; end if;
 if not exists(select 1 from classroom_private.profiles p join auth.users u on p.id=u.id where p.id=p_user and u.email_confirmed_at is not null) then raise exception 'verified profile required' using errcode='22023'; end if;
 insert into classroom_private.supporters(user_id,state,checked_at,checked_by,access_basis) values(p_user,p_state,case when p_state<>'qualified' or p_minimum_confirmed is true then now() else null end,auth.uid(),case when p_state='qualified' and p_minimum_confirmed is not true then 'self_declared' else 'payment_checked' end)
 on conflict(user_id) do update set state=excluded.state,checked_at=excluded.checked_at,checked_by=excluded.checked_by,access_basis=excluded.access_basis;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'supporter_'||p_state,p_user::text);
end $$;

create or replace function classroom_private.claim_supporter_notice(p_user uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare claimed uuid;
begin
 update classroom_private.supporter_notices set state='sending',attempted_at=now()
 where user_id=p_user and sent_at is null and (attempted_at is null or attempted_at<now()-interval '1 minute')
 returning user_id into claimed;
 if claimed is null then return null; end if;
 return (select jsonb_build_object('user_id',p.id,'name',p.name,'email',u.email,'created_at',n.created_at,'supporter_state',(select s.state from classroom_private.supporters s where s.user_id=p.id))
 from classroom_private.profiles p join auth.users u on u.id=p.id join classroom_private.supporter_notices n on n.user_id=p.id where p.id=claimed);
end $$;
notify pgrst,'reload schema';
commit;
