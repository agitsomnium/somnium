-- User decision: show lectures only. Retain Q&A records and original media.
begin;
insert into classroom_private.audit(actor,action,target)
 select a.user_id,'lesson_hidden_qa',l.id::text
 from classroom_private.lessons l cross join (select user_id from classroom_private.admins where enabled order by user_id limit 1) a
 where l.published and normalize(l.title,NFC) ~* '질의[[:space:]]*응답|질문[[:space:]]*(과|및|&)?[[:space:]]*(답변|응답)|(^|[^[:alnum:]])q[[:space:]]*(&|and|n|/)[[:space:]]*a([^[:alnum:]]|$)';
update classroom_private.lessons set published=false
 where published and normalize(title,NFC) ~* '질의[[:space:]]*응답|질문[[:space:]]*(과|및|&)?[[:space:]]*(답변|응답)|(^|[^[:alnum:]])q[[:space:]]*(&|and|n|/)[[:space:]]*a([^[:alnum:]]|$)';
alter table classroom_private.lessons add constraint published_lectures_only
 check (not published or normalize(title,NFC) !~* '질의[[:space:]]*응답|질문[[:space:]]*(과|및|&)?[[:space:]]*(답변|응답)|(^|[^[:alnum:]])q[[:space:]]*(&|and|n|/)[[:space:]]*a([^[:alnum:]]|$)');
commit;
