begin;
-- HTML stays in private storage and is displayed in an opaque sandbox, never a public route.
alter table classroom_private.accounting_reports drop constraint accounting_reports_filename_check;
alter table classroom_private.accounting_reports add constraint accounting_reports_filename_check check(char_length(filename) between 1 and 220 and filename !~ '[/\\]' and filename ~* '[.](pdf|html)$');
alter table classroom_private.accounting_reports drop constraint accounting_reports_storage_path_check;
alter table classroom_private.accounting_reports add constraint accounting_reports_storage_path_check check(storage_path ~ '^[a-f0-9-]{36}[.](pdf|html)$');
update storage.buckets set allowed_mime_types=array['application/pdf','text/html'] where id='somnium-accounting' and not public;
create or replace function classroom_private.save_report(p_title text,p_period text,p_filename text,p_path text,p_enabled boolean default true) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid; expected_mime text;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501';end if;
 expected_mime:=case when p_filename ~* '[.]html$' and p_path ~ '[.]html$' then 'text/html' when p_filename ~* '[.]pdf$' and p_path ~ '[.]pdf$' then 'application/pdf' else null end;
 if expected_mime is null or not exists(select 1 from storage.objects where bucket_id='somnium-accounting' and name=p_path and metadata->>'mimetype'=expected_mime and (metadata->>'size')::bigint between 1 and 26214400) then raise exception 'uploaded matching report required' using errcode='22023';end if;
 insert into classroom_private.accounting_reports(title,period,filename,storage_path,created_by,enabled) values(btrim(p_title),btrim(coalesce(p_period,'')),p_filename,p_path,auth.uid(),p_enabled) returning id into result;
 insert into classroom_private.audit(actor,action,target) values(auth.uid(),'accounting_report_added',result::text);
 return result;
end$$;
drop policy somnium_accounting_upload on storage.objects;
create policy somnium_accounting_upload on storage.objects for insert to authenticated with check(bucket_id='somnium-accounting' and name ~ '^[a-f0-9-]{36}[.](pdf|html)$' and classroom_private.is_admin());
commit;
