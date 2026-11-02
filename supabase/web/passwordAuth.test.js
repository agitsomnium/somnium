import test from 'node:test';
import assert from 'node:assert/strict';
import {passwordAuth, passwordProblem, authMessage} from './passwordAuth.js';

function fixture(user = {email:'member@example.invalid', email_confirmed_at:'2026-11-02'}) {
  const calls = [];
  const auth = Object.fromEntries(['signInWithOtp','verifyOtp','signInWithPassword','updateUser'].map(method => [method, async args => {
    calls.push([method, args]); return {data:{user}, error:null};
  }]));
  auth.getUser = async () => ({data:{user}, error:null});
  return {service:passwordAuth(auth), calls};
}
test('password login does not request an email or create a new account', async () => {
  const {service,calls}=fixture();
  await service.login('member@example.invalid','test-password-only');
  assert.deepEqual(calls, [['signInWithPassword',{email:'member@example.invalid',password:'test-password-only'}]]);
});
test('signup alone may create an account; existing-member setup cannot create one', async () => {
  const {service,calls}=fixture();
  await service.requestCode('member@example.invalid',true);
  await service.requestCode('member@example.invalid',false);
  assert.deepEqual(calls.map(x=>x[1].options.shouldCreateUser),[true,false]);
});
test('verification uses email OTP; password update only contains password', async () => {
  const {service,calls}=fixture();
  await service.verifyCode('member@example.invalid','123456');
  await service.setPassword('member@example.invalid','test-password-only','test-password-only');
  assert.deepEqual(calls,[['verifyOtp',{email:'member@example.invalid',token:'123456',type:'email'}],['updateUser',{password:'test-password-only'}]]);
});
for (const [name,user] of [['anonymous',null],['unverified',{email:'member@example.invalid'}],['different account',{email:'other@example.invalid',email_confirmed_at:'2026-11-02'}]]) {
  test(`cannot set password for ${name}`, async()=>{
    const {service,calls}=fixture(user);
    await assert.rejects(service.setPassword('member@example.invalid','test-password-only','test-password-only'),/먼저 인증/);
    assert.equal(calls.length,0);
  });
}
test('mismatched, short and oversized passwords do not reach Auth',async()=>{
  const {service,calls}=fixture();
  for(const [a,b] of [['short','short'],['test-password-only','different-password'],['x'.repeat(129),'x'.repeat(129)]]) {
    await assert.rejects(service.setPassword('member@example.invalid',a,b));
  }
  assert.equal(calls.length,0);
  assert.equal(passwordProblem('long pass phrase','long pass phrase'),'');
});
test('known errors explain first-time setup and mismatches',()=>{
  assert.match(authMessage({code:'invalid_credentials'}),/처음 설정/);
  assert.match(authMessage({code:'email_not_confirmed'}),/인증번호/);
});
