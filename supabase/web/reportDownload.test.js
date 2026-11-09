import test from 'node:test';import assert from 'node:assert/strict';
import {downloadReport} from './reportDownload.js';
const report={id:'r',path:'r.pdf',filename:'보고서.pdf'};
function setup(){let state={userId:'member',epoch:1,canReadReports:true};let rows=[report],offered=0,downloads=0;return {
 setState:v=>state=v,setRows:v=>rows=v,get offered(){return offered;},get downloads(){return downloads;},
 deps:{access:()=>state,list:async()=>rows,download:async()=>{downloads++;return 'blob';},offer:()=>offered++}};}
test('authorized director can download without supporter qualification',async()=>{const x=setup();assert.equal(await downloadReport(report,x.deps),true);assert.equal(x.offered,1);});
test('anonymous report download makes no storage call',async()=>{const x=setup();x.setState({canReadReports:false});await assert.rejects(downloadReport(report,x.deps));assert.equal(x.downloads,0);});
test('a hidden or mismatched report is rejected before storage',async()=>{const x=setup();x.setRows([{...report,path:'other.pdf'}]);await assert.rejects(downloadReport(report,x.deps));assert.equal(x.downloads,0);});
test('logout during download suppresses offering',async()=>{const x=setup();x.deps.download=async()=>{x.setState({canReadReports:false});return 'blob';};assert.equal(await downloadReport(report,x.deps),false);assert.equal(x.offered,0);});
test('account switch or epoch change suppresses offering',async()=>{for(const state of [{userId:'other',epoch:1,canReadReports:true},{userId:'member',epoch:2,canReadReports:true}]){const x=setup();x.deps.download=async()=>{x.setState(state);return 'blob';};assert.equal(await downloadReport(report,x.deps),false);}});
test('hiding report during download suppresses offering after fresh server check',async()=>{const x=setup();x.deps.download=async()=>{x.setRows([]);return 'blob';};assert.equal(await downloadReport(report,x.deps),false);assert.equal(x.offered,0);});

test('ordinary or supporter membership alone cannot download accounting',async()=>{const x=setup();x.setState({userId:'member',member:true,canReadReports:false});await assert.rejects(downloadReport(report,x.deps));assert.equal(x.downloads,0);});
