-- Thumbnail metadata stays behind the same live membership check as the catalog.
begin;
create or replace function classroom_private.catalog() returns jsonb
 language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object(
 'id',id,'title',title,'description',description,'series_title',series_title,
 'position',position,'era',era,
 'thumbnail_url',case when provider='youtube' then 'https://i.ytimg.com/vi/'||video_id||'/mqdefault.jpg' else null end
 ) order by series_title,position,id),'[]'::jsonb)
 from classroom_private.lessons where published and classroom_private.can_learn()
$$;
commit;
