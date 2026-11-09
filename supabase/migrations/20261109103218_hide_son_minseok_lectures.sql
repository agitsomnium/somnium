-- User request 2026-11-09: hide all Son Min-seok lectures, preserving records.
begin;
update classroom_private.lessons set published=false
where normalize(title,NFC) like '%손민석%' or normalize(description,NFC) like '%손민석%' or normalize(series_title,NFC) like '%손민석%';
commit;
select count(*) filter(where published) as still_visible,
 count(*) as total_recordings
from classroom_private.lessons
where normalize(title,NFC) like '%손민석%' or normalize(description,NFC) like '%손민석%' or normalize(series_title,NFC) like '%손민석%';
