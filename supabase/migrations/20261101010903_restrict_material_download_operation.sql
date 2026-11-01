-- Download with the current JWT on every request; do not permit signed-link creation.
begin;
alter policy somnium_material_read on storage.objects using(
 bucket_id='somnium-materials'
 and storage.allow_only_operation('storage.object.get_authenticated')
 and classroom_private.can_read_material(name)
);
commit;
