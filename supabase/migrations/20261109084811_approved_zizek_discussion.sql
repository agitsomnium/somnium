-- 2026-11-09 user: include the specifically approved Zizek discussion in its lecture set.
-- All other Q&A rows remain hidden unless separately approved.
begin;
alter table classroom_private.lessons drop constraint published_lectures_only;
alter table classroom_private.lessons add constraint published_lectures_only
 check(not published or id='383cfced-2fe6-5f96-ba64-a7c43db2a0b4'::uuid or normalize(title,NFC) !~* '질의[[:space:]]*응답|질문[[:space:]]*(과|및|&)?[[:space:]]*(답변|응답)|(^|[^[:alnum:]])q[[:space:]]*(&|and|n|/)[[:space:]]*a([^[:alnum:]]|$)');
commit;
