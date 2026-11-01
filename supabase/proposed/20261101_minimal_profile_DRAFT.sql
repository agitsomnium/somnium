-- DRAFT · NOT APPLIED to any database. Local isolated PostgreSQL review only.
-- Goal: sign-up needs name + verified e-mail; phone optional; birth date no longer collected.
-- Preserves: every existing profile row (name, birth, phone, consent, suspension), supporter state,
-- director roster, series entitlements. Nothing is deleted or rewritten for existing members.
-- The old public.somnium_complete_profile(text,date,text,boolean) stays callable until the UI switches.
begin;

alter table classroom_private.profiles alter column birth drop not null;
alter table classroom_private.profiles alter column phone drop not null;
alter table classroom_private.profiles add column supporter_name text
 check (supporter_name is null or char_length(supporter_name) between 2 and 40);

create function classroom_private.complete_profile_minimal(p_name text,p_phone text,p_supporter_name text,p_consent boolean) returns void
 language plpgsql security definer set search_path='' as $$
declare v_phone text := nullif(regexp_replace(coalesce(p_phone,''),'[-[:space:]]','','g'),'');
        v_supporter text := nullif(btrim(coalesce(p_supporter_name,'')),'');
begin
 if not classroom_private.verified() then raise exception 'email verification required' using errcode='42501'; end if;
 if p_consent is distinct from true then raise exception 'consent required' using errcode='22023'; end if;
 if v_phone is not null and v_phone !~ '^01[0-9]{8,9}$' then raise exception 'invalid phone' using errcode='22023'; end if;
 insert into classroom_private.profiles(id,name,phone,supporter_name,consent_version)
 values(auth.uid(),btrim(p_name),v_phone,v_supporter,'somnium-v2-minimal-draft')
 on conflict(id) do update set name=excluded.name,
  phone=coalesce(excluded.phone,classroom_private.profiles.phone),
  supporter_name=coalesce(excluded.supporter_name,classroom_private.profiles.supporter_name);
 -- Existing birth, suspension, consent version/time are not touched by re-registering.
end $$;

-- Admin list: stop returning birth date (stored values are kept); add the optional supporter name.
create or replace function classroom_private.admin_members() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 return (select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'phone',p.phone,'supporter_name',p.supporter_name,
 'email',u.email,'suspended',p.suspended,'supporter_state',coalesce(s.state,'not_requested')) order by p.name),'[]'::jsonb)
 from classroom_private.profiles p join auth.users u on p.id=u.id left join classroom_private.supporters s on s.user_id=p.id);
end $$;

create function public.somnium_complete_profile_minimal(p_name text,p_phone text,p_supporter_name text,p_consent boolean) returns void
 language sql security invoker set search_path='' as $$ select classroom_private.complete_profile_minimal(p_name,p_phone,p_supporter_name,p_consent) $$;

revoke all on function classroom_private.complete_profile_minimal(text,text,text,boolean) from public,anon,authenticated;
grant execute on function classroom_private.complete_profile_minimal(text,text,text,boolean) to authenticated;
revoke all on function public.somnium_complete_profile_minimal(text,text,text,boolean) from public,anon,authenticated;
grant execute on function public.somnium_complete_profile_minimal(text,text,text,boolean) to authenticated;
commit;
