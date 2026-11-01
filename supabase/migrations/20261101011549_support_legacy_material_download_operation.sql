-- The hosted Storage service uses the legacy authenticated-info operation for GET.
begin;
alter policy somnium_material_read on storage.objects using(
 bucket_id='somnium-materials'
 and storage.allow_any_operation(array['storage.object.get_authenticated','object.get_authenticated_info'])
 and classroom_private.can_read_material(name)
);
drop function if exists classroom_private.debug_material_read(text);
commit;
