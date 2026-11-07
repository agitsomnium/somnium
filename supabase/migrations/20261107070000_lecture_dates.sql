begin;
alter table classroom_private.lessons add column if not exists lecture_date date;
update classroom_private.lessons set published=false where id='fa80b3bc-af82-5428-ab73-cd218a94f4e5';
update classroom_private.lessons l set lecture_date=v.lecture_date from (values
('6a30092e-9386-559f-b8eb-e7c47c179e73'::uuid,'2018-04-11'::date),
('93e9dc46-c677-5fad-8248-69b706e41dfd'::uuid,'2018-04-19'::date),
('589f3e6e-1c59-5af3-87ee-9ff2915e715c'::uuid,'2018-03-08'::date),
('c7006017-1395-5c8d-9570-d328c3830818'::uuid,'2019-08-22'::date),
('30bc8e7d-19ea-5950-b6ce-3f84d080f06d'::uuid,'2019-04-25'::date),
('b92c5a13-5ae7-5c0b-af59-7a6e08183e6b'::uuid,'2019-04-25'::date),
('8818adee-8ae9-5ace-9522-32eb1cc19b58'::uuid,'2020-05-06'::date),
('e5f9aca3-6846-5485-9964-d915551cdd30'::uuid,'2020-06-03'::date),
('017a856e-84de-5be2-b45e-6480e474252e'::uuid,'2020-09-16'::date),
('c4deb83c-9026-50e4-8097-6545bca1cfb6'::uuid,'2020-09-17'::date),
('06053fbc-cd01-5ebf-a30b-314e0327ed0a'::uuid,'2020-05-21'::date),
('63577520-9a1e-5abc-8a7f-6ef050bad9ad'::uuid,'2020-05-28'::date),
('a90f6b03-f3d4-5d78-9064-9620602b4927'::uuid,'2020-08-27'::date),
('347ad65e-df86-565b-8ccf-f2d1d246aff5'::uuid,'2022-02-23'::date),
('ac85f7a0-604f-51f2-b9aa-2340550aec17'::uuid,'2022-03-02'::date),
('ca3eb284-3361-5d0d-8f3a-197602850dfe'::uuid,'2022-03-23'::date),
('ebd99f82-d0f1-5198-a526-aaaf7a18b2a3'::uuid,'2022-03-17'::date),
('aa3c3276-a4fa-5282-bde3-fdc698013c1c'::uuid,'2022-04-21'::date),
('cfe654e1-a544-5e85-8158-dd50ddc05c13'::uuid,'2022-06-02'::date),
('28973e4a-41a4-519a-b922-8e7df88adc9c'::uuid,'2022-06-16'::date),
('3d355846-ca65-5ac4-bff9-796f978e2ee2'::uuid,'2024-08-22'::date),
('5c7d3129-92b7-5b58-b6e9-e1f1028b9ef1'::uuid,'2024-08-29'::date),
('5218d140-0231-57f0-a2b6-be24031679c0'::uuid,'2024-09-05'::date),
('c41c2254-c87d-589b-810f-4d29765ff296'::uuid,'2024-10-17'::date),
('334e5268-efc1-5d25-adcc-34e524cc1ee2'::uuid,'2024-10-24'::date),
('4b4a2c6c-5a06-5e9c-a88f-e6fe8f4d9326'::uuid,'2024-10-31'::date),
('99a669dd-5449-569b-94d9-2a76928057e7'::uuid,'2021-06-24'::date),
('7ac3487c-47aa-504f-8716-2f3d3f140684'::uuid,'2021-07-01'::date),
('4645ff52-4f2f-56c9-a10b-5bd15661c9b7'::uuid,'2021-07-08'::date),
('4bc19cb0-140f-5e89-b425-02331f0c3410'::uuid,'2021-07-15'::date),
('4215bbae-9cf7-5388-9b63-8fe08e6fa838'::uuid,'2025-08-05'::date),
('3e10c77e-2151-596a-8afd-52fde94c94d0'::uuid,'2025-07-15'::date),
('8f76309e-2828-5171-8661-f30274982eb3'::uuid,'2025-04-17'::date),
('b1fac215-ec81-51ca-889a-f781d4f65554'::uuid,'2025-04-10'::date),
('1b5f2768-ef1b-58f2-babf-cea9336af811'::uuid,'2025-04-03'::date),
('78561992-19f4-5826-a7e4-d4c4da136bc3'::uuid,'2021-03-18'::date),
('d3777014-63ca-5038-b03f-0b795afbba65'::uuid,'2021-04-22'::date),
('376f590e-d709-5f42-ba55-7b7aaaabc2d5'::uuid,'2021-05-27'::date),
('793327e3-8104-5a43-aa8c-1d15edd9c12f'::uuid,'2021-09-02'::date),
('ec543b5a-e248-537c-bcab-007cf4d08cb8'::uuid,'2021-09-09'::date),
('e893e33d-afb1-556b-b862-5b949327d46e'::uuid,'2022-06-08'::date),
('952a5bb8-4274-55c9-ba5a-fcbcda7fa061'::uuid,'2022-07-06'::date),
('0d1f646f-79af-5386-aecb-631d3c774919'::uuid,'2020-11-12'::date),
('dcbdaa3f-82ae-52e8-868c-52c02e21635e'::uuid,'2020-11-12'::date),
('cee28164-f707-5738-91e6-6d876c2d22e1'::uuid,'2020-11-18'::date),
('3f2aa92d-19a4-580d-8544-822b4f1c11bc'::uuid,'2020-11-18'::date),
('ba3d2355-6118-5d91-9453-52d4017b41ab'::uuid,'2020-11-19'::date),
('7e9aa09e-ac63-5c72-b8c9-5d19aa196f06'::uuid,'2020-11-19'::date),
('b6a2d5aa-ac30-5c7b-ba38-d74c254b131b'::uuid,'2021-05-28'::date),
('772d14b2-fb88-5b55-af5e-4912e82bdcb4'::uuid,'2021-09-12'::date),
('268c475a-97c9-54dd-977c-fd190a1e6b8b'::uuid,'2021-11-19'::date),
('0b060947-5285-56fc-8706-b96ae53d8015'::uuid,'2021-12-09'::date),
('5c629acb-0626-5bbc-ae57-dfa32be44c26'::uuid,'2022-06-14'::date),
('d3bd0a67-8161-58b9-a051-841861c83501'::uuid,'2022-08-03'::date),
('ed0c6a74-7bbd-5dc4-9ebc-1614ec2662f3'::uuid,'2022-09-08'::date),
('c3b18b0e-ebb5-5ae5-b611-90d2e1031c75'::uuid,'2022-09-22'::date),
('99622a82-f241-5b90-a7d9-4196b29c19ed'::uuid,'2022-09-29'::date),
('e9aca43e-4d89-5d8a-be9f-abc4c8896acc'::uuid,'2022-10-13'::date),
('48b3668c-6286-5102-818f-6914740e7a28'::uuid,'2022-10-20'::date),
('6cf85023-4139-59b3-a284-1a238288230d'::uuid,'2022-12-08'::date),
('ea96484c-964b-5c82-ab3d-cc43b0cc9084'::uuid,'2023-03-16'::date),
('d0385e66-7e2d-59fa-a795-f6c2b048f55f'::uuid,'2023-03-30'::date),
('26e605b7-d91c-57ae-b15c-10e76aead9af'::uuid,'2023-04-06'::date),
('d3c000e8-fe9f-5797-a4ff-67c2a227636a'::uuid,'2023-05-04'::date),
('3d77af5a-f420-5a57-a795-266d6cb58036'::uuid,'2023-06-01'::date),
('e88d743c-e600-511d-86ed-bca1df0ca8f0'::uuid,'2023-06-15'::date),
('122a7f44-7fc1-5d06-93a8-faec12271485'::uuid,'2023-06-22'::date),
('9f63d0ea-54b5-5d1d-ae80-54d78c189834'::uuid,'2023-08-31'::date),
('cf7b5c3e-a282-5f5a-b010-df2e0a6d217a'::uuid,'2023-09-14'::date),
('ad1bfd89-65ff-54e3-940a-d72b32d6864c'::uuid,'2024-04-18'::date),
('74ab4577-ff53-538a-bd88-80bb76090b7d'::uuid,'2024-05-09'::date),
('8c40cc32-0981-5d19-aef1-b6a834bd86e3'::uuid,'2024-07-04'::date),
('1b20fda9-b3e8-563b-bccc-d16efb9b7c17'::uuid,'2024-07-18'::date),
('094a332d-1dad-5580-98bc-ae9bff05a9b4'::uuid,'2024-07-11'::date),
('41079897-f65e-50e8-888d-5303b8127b9a'::uuid,'2026-09-17'::date),
('40c6534f-bb62-5d70-9d9f-a2a35f2ec209'::uuid,'2026-10-01'::date),
('403657d2-f922-503c-b3a6-779b4ee9c450'::uuid,'2026-10-08'::date),
('7b2213ef-65e2-57b0-ab45-78f09813060c'::uuid,'2026-10-15'::date),
('ca913200-3ffd-5a7f-a153-76ffed22be70'::uuid,'2026-10-22'::date),
('9f0d7346-a590-5bc2-a2f8-55a670c41949'::uuid,'2026-10-29'::date),
('b0e37079-91bc-55ee-9df4-750c54ad7f27'::uuid,'2021-03-10'::date),
('9c296e55-bc3b-5b2c-ad5c-ab9301ae2102'::uuid,'2021-03-17'::date),
('9896970c-6612-53ed-a036-95adecd2057d'::uuid,'2021-03-24'::date),
('289a3310-b67c-5cfe-a3f5-150afd941fec'::uuid,'2021-03-31'::date),
('0fd7cf03-23e2-569e-b9e3-cac4598941ea'::uuid,'2021-04-14'::date),
('a1b80a5b-6361-5572-bc69-977be8f57f52'::uuid,'2021-04-21'::date),
('0a20eb81-c04a-5cec-bd31-faf617d2be27'::uuid,'2021-04-28'::date),
('2c0c48a6-0a4d-51c1-ac34-d078f48548be'::uuid,'2021-09-28'::date),
('0abab20e-90c8-5e48-a38c-68ebda77c2c3'::uuid,'2021-10-05'::date),
('462a600e-2061-5fb6-b7ae-0525edabb53a'::uuid,'2021-10-12'::date),
('26845630-78a5-51cd-a1fb-a6572662bd2a'::uuid,'2021-10-26'::date),
('a1480f1e-2386-5f31-8619-5ebdfa40f22f'::uuid,'2021-11-02'::date),
('eb7a4766-995f-547c-9208-496401f9642c'::uuid,'2026-07-23'::date),
('92bae007-deca-5865-a79f-b38926362ca2'::uuid,'2026-07-30'::date),
('ee27b792-0581-5ad2-86e1-ed706319919d'::uuid,'2026-08-06'::date)) as v(id,lecture_date) where l.id=v.id;
alter table classroom_private.lessons add constraint published_lecture_date_required check(not published or lecture_date is not null);
alter table classroom_private.lessons add constraint lecture_date_range check(lecture_date is null or lecture_date between date '2000-01-01' and date '2099-12-31');
create or replace function public.somnium_public_catalog() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object(
 'id',id,'title',title,'description',description,'series_title',series_title,
 'position',position,'era',era,'lecture_date',lecture_date,
 'thumbnail_url',case when provider='youtube' then '/assets/lecture-covers/'||id::text||'.jpg' else null end
 ) order by lecture_date desc,position,id),'[]'::jsonb)
 from classroom_private.lessons where published;
$$;
create function classroom_private.save_lesson(p_id uuid,p_title text,p_description text,p_series text,p_position integer,p_era text,p_published boolean,p_provider text,p_video_id text,p_video_privacy text,p_lecture_date date) returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not classroom_private.is_admin() then raise exception 'admin required' using errcode='42501'; end if;
 if p_published and p_lecture_date is null then raise exception 'lecture date required' using errcode='22023'; end if;
 result:=classroom_private.save_lesson(p_id,p_title,p_description,p_series,p_position,p_era,false,p_provider,p_video_id,p_video_privacy);
 update classroom_private.lessons set lecture_date=p_lecture_date,published=p_published where id=result;
 return result;
end $$;
revoke all on function classroom_private.save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text,date) from public,anon;
grant execute on function classroom_private.save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text,date) to authenticated;
create function public.somnium_save_lesson(p_id uuid,p_title text,p_description text,p_series text,p_position integer,p_era text,p_published boolean,p_provider text,p_video_id text,p_video_privacy text,p_lecture_date date) returns uuid
language sql security invoker set search_path='' as $$ select classroom_private.save_lesson(p_id,p_title,p_description,p_series,p_position,p_era,p_published,p_provider,p_video_id,p_video_privacy,p_lecture_date) $$;
revoke all on function public.somnium_save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text,date) from public,anon;
grant execute on function public.somnium_save_lesson(uuid,text,text,text,integer,text,boolean,text,text,text,date) to authenticated;
notify pgrst,'reload schema';
commit;
select count(*) filter(where published) as published,count(*) filter(where published and lecture_date is null) as missing_dates from classroom_private.lessons;
