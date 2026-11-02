-- Public promotional metadata only. Playback, file paths and source video IDs stay in existing protected RPCs.
begin;
create function public.somnium_public_catalog() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object(
 'id',id,'title',title,'description',description,'series_title',series_title,
 'position',position,'era',era,
 'thumbnail_url',case when provider='youtube' then '/assets/lecture-covers/'||id::text||'.jpg' else null end
 ) order by series_title,position,id),'[]'::jsonb)
 from classroom_private.lessons where published;
$$;
revoke all on function public.somnium_public_catalog() from public;
grant execute on function public.somnium_public_catalog() to anon,authenticated;
comment on function public.somnium_public_catalog() is 'Public approved lecture titles/descriptions and locally mirrored covers, never source media identifiers or resource paths.';
commit;
