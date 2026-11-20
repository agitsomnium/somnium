import test from 'node:test';
import assert from 'node:assert/strict';
import {applyActivityEdits,isActivityPaper} from './activityEdit.js';
const data={version:'somnium-activity-paper/1',programs:[{name:'가',applied:3,assess:['[평가 입력 필요] 가']},{name:'나',applied:2,assess:['유지']}],channels:{youtube:{meta:'옛'},instagram:{meta:'옛'}}};
const page=d=>'<style>x</style><script id="report-data" type="application/json">'+JSON.stringify(d)+'</script><script>run()</script>';
const read=body=>JSON.parse(body.split('type="application/json">')[1].split('</script>')[0]);
test('assessment and channel text change; everything else stays',()=>{
  const out=applyActivityEdits(page(data),{assess:{0:['첫 평가 <b>','  ','둘째 & 셋째']},channels:{youtube:'구독자 100명'}});
  const d=read(out);
  assert.deepEqual(d.programs[0].assess,['첫 평가 <b>','둘째 & 셋째']);
  assert.deepEqual(d.programs[1],data.programs[1]);assert.equal(d.programs[0].applied,3);
  assert.equal(d.channels.youtube.meta,'구독자 100명');assert.equal(d.channels.instagram.meta,'옛');
  assert.ok(!out.split('type="application/json">')[1].split('</script>')[0].includes('<'));
  assert.ok(out.startsWith('<style>x</style>')&&out.endsWith('<script>run()</script>'));
});
test('refuses other papers, unknown fields and contact details',()=>{
  assert.equal(isActivityPaper('<p>somnium-finance-paper/1</p>'),false);
  assert.throws(()=>applyActivityEdits('<p>x</p>',{}));
  assert.throws(()=>applyActivityEdits(page(data),{assess:{9:['x']}}));
  assert.throws(()=>applyActivityEdits(page(data),{assess:{0:'x'}}));
  assert.throws(()=>applyActivityEdits(page(data),{channels:{facebook:'x'}}));
  assert.throws(()=>applyActivityEdits(page(data),{assess:{0:['문의 010-1234-5678']}}));
  assert.throws(()=>applyActivityEdits(page(data),{assess:{0:['a@b.co']}}));
  assert.throws(()=>applyActivityEdits(page(data),{assess:{0:['x'.repeat(601)]}}));
});
