import test from 'node:test';
import assert from 'node:assert/strict';
import { newestFirst } from './order.js';
const row=(id,title,series_title='',position=1,era='archive')=>({id,title,series_title,position,era});
test('newest session first; book publication years do not reorder the capitalism series',()=>{
 const rows=[row('one','세미나01','현대 자본주의 이해하기',1,'current'),row('six','『생명의 그물 속자본주의』(2020)','현대 자본주의 이해하기',6,'current'),row('old','강의_25.08.5')];
 assert.deepEqual(newestFirst(rows).map(x=>x.id),['six','one','old']);
 assert.equal(rows[0].id,'one');
});
test('full, short and compact dates sort by session date',()=>{
 assert.deepEqual(newestFirst([row('a','230316 강의'),row('b','강의_2020.11.12'),row('c','강의_25.4.3')]).map(x=>x.id),['c','a','b']);
});
test('split recordings on the same day keep their part order',()=>{
 assert.deepEqual(newestFirst([row('two','강의(2)_2020.11.12','시리즈',2),row('one','강의(1)_2020.11.12','시리즈',1)]).map(x=>x.id),['one','two']);
});
test('year-only sessions use the known year, not an invented exact date',()=>{
 assert.deepEqual(newestFirst([row('old','2018 강의'),row('new','2024 강의'),row('dated','강의_2024.5.9')]).map(x=>x.id),['dated','new','old']);
});
test('a month/day inherits a year only from an unambiguous series',()=>{
 assert.deepEqual(newestFirst([row('september','벤야민_9.9','2021 세미나'),row('may','강의_2021.5.27','2021 세미나')]).map(x=>x.id),['september','may']);
});

test('undated lectures in one known year use the latest recorded series order first',()=>{
 assert.deepEqual(newestFirst([row('one','2024 첫 강의','2024 시리즈',1),row('last','2024 마지막 강의','2024 시리즈',12)]).map(x=>x.id),['last','one']);
});
