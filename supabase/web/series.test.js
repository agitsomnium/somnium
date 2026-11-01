import test from 'node:test';
import assert from 'node:assert/strict';
import { seriesGroups } from './series.js';
const r=(id,series_title,era='archive')=>({id,series_title,era});
test('all actual series are bundled while first encounter keeps newest-first group order',()=>{
 const rows=[r('modern6','현대 자본주의 이해하기','current'),r('modern5','현대 자본주의 이해하기','current'),r('old2','2024 정치신학'),r('old1','2024 정치신학')];
 const groups=seriesGroups(rows);
 assert.equal(groups[0].name,'현대자본주의 세미나 1');
 assert.equal(groups[0].key,'modern-capitalism-2026');
 assert.deepEqual(groups.map(g=>g.lessons.map(x=>x.id)),[['modern6','modern5'],['old2','old1']]);
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
