import test from 'node:test';
import assert from 'node:assert/strict';
import { seriesGroups } from './series.js';
const r=(id,series_title,era='archive')=>({id,series_title,era,title:id,position:Number(id.match(/\d+$/)?.[0]||0)});
test('all actual series are bundled while first encounter keeps newest-first group order',()=>{
 const rows=[r('modern6','현대 자본주의 이해하기','current'),r('modern5','현대 자본주의 이해하기','current'),r('old2','2024 정치신학'),r('old1','2024 정치신학')];
 const groups=seriesGroups(rows);
 assert.equal(groups[0].name,'현대자본주의 세미나 1');
 assert.equal(groups[0].key,'modern-capitalism-2026');
 assert.deepEqual(groups.map(g=>g.lessons.map(x=>x.id)),[['modern5','modern6'],['old1','old2']]);
 assert.ok(groups.every(g=>g.bundled));
 assert.equal(rows.length,4);
});
test('archive categories and independent lectures are not sold or presented as invented series',()=>{
 const groups=seriesGroups([r('a','이전 솜니움 강좌'),r('b','이전 솜니움 강좌'),r('c',''),r('d','솜니움 이전 강좌 · 2025~2026')]);
 assert.equal(groups.length,4);assert.ok(groups.every(g=>!g.bundled));
});
test('same title in different eras stays separate',()=>{
 assert.equal(seriesGroups([r('a','시리즈','archive'),r('b','시리즈','future')]).length,2);
});

test('capitalism and Spinoza collapse separately and expand in chronological course order',()=>{
 const rows=[
  {...r('capital6','현대 자본주의 이해하기','current'),lecture_date:'2026-10-29',position:6},
  {...r('spinoza3','스피노자 세미나'),lecture_date:'2026-08-06',position:3},
  {...r('capital1','현대 자본주의 이해하기','current'),lecture_date:'2026-09-17',position:1},
  {...r('spinoza1','스피노자 세미나'),lecture_date:'2026-07-23',position:1},
  {...r('solo',''),lecture_date:'2025-07-15'}];
 const original=JSON.stringify(rows),groups=seriesGroups(rows);
 assert.deepEqual(groups.map(g=>g.lessons.map(l=>l.id)),[['capital1','capital6'],['spinoza1','spinoza3'],['solo']]);
 assert.equal(JSON.stringify(rows),original);
});
