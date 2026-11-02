import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeCatalog,localCover} from './publicCatalog.js';
const rows=[{id:'a',title:'A'},{id:'b',title:'B'}];
test('anonymous and ordinary members browse all lectures without playback entitlement',()=>{
  assert.deepEqual(mergeCatalog(rows,[]).map(x=>x.available),[false,false]);
});
test('a series pass unlocks only returned entitled lectures, preserving public list',()=>{
  const result=mergeCatalog(rows,[{id:'a',title:'A',thumbnail_url:'private'}]);
  assert.equal(result.length,2);assert.equal(result[0].available,true);assert.equal(result[1].available,false);
});
test('revoking access immediately removes private metadata from next rendered catalog',()=>{
  const allowed=mergeCatalog(rows,[{id:'a',thumbnail_url:'private'}]);
  assert.equal(allowed[0].thumbnail_url,'private');
  const revoked=mergeCatalog(rows,[]);assert.equal(revoked[0].thumbnail_url,undefined);assert.equal(revoked[0].available,false);
});
test('public cover accepts only fixed local image paths, never arbitrary media URLs',()=>{
  assert.equal(localCover('/assets/lecture-covers/12345678-1234-1234-1234-123456789abc.jpg'),true);
  for(const url of ['https://i.ytimg.com/vi/example/mqdefault.jpg','/assets/lecture-covers/../../secret.jpg','javascript:alert(1)',null]) assert.equal(localCover(url),false);
});
