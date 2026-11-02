// Run the actual app event handlers with a DOM/Auth double; no real credentials or network.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {passwordAuth,authMessage} from './passwordAuth.js';
import {entryMode} from './entryMode.js';
import {catalogPlan} from './catalogView.js';
import {newestFirst} from './order.js';
import {seriesGroups} from './series.js';
import {mergeCatalog,localCover} from './publicCatalog.js';
const source=readFileSync(new URL('./app.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
async function harness({existing=false, pending=false, verifyError=null, hasProfile=true}={}) {
  const nodes=new Map(), storage=new Map(pending?[['somnium-password-pending','yes']]:[]), calls=[];
  const field=()=>({value:'',disabled:false,required:false,focus(){},reportValidity(){return !!this.value;}});
  function node(id) {
    if (!nodes.has(id)) nodes.set(id,{id,hidden:true,value:'',textContent:'',disabled:false,childElementCount:0,
      elements:{email:field(),password:field(),confirmation:field(),token:field(),id:field()},
      setAttribute(){},querySelector(){return node(id+'-submit');},querySelectorAll(){return [];},
      append(){this.childElementCount++;},replaceChildren(){this.childElementCount=0;},scrollIntoView(){},focus(){},reset(){for(const f of Object.values(this.elements)) f.value='';}});
    return nodes.get(id);
  }
  let current=existing?{id:'member-1',email:'member@example.invalid',email_confirmed_at:'2026-11-02'}:null;
  let callback;
  const auth={
    getUser:async()=>({data:{user:current},error:null}),
    onAuthStateChange(fn){callback=fn;},
    async signInWithPassword(args){calls.push(['login',args]);current={id:'member-1',email:args.email,email_confirmed_at:'2026-11-02'};return {error:null};},
    async signInWithOtp(args){calls.push(['code',args]);return {error:null};},
    async verifyOtp(args){calls.push(['verify',args]);if(!verifyError) current={id:'member-1',email:args.email,email_confirmed_at:'2026-11-02'};return {error:verifyError};},
    async updateUser(args){calls.push(['password',args]);return {error:null};},
    async signOut(){current=null;callback('SIGNED_OUT');return {error:null};},
  };
  const db={auth,rpc:async(name)=>{calls.push(['rpc',name]);return {data:name==='somnium_me'?(hasProfile?{name:'시험회원',can_learn:false,admin:false,full_access:false,supporter_state:'not_requested'}:null):[],error:null};}};
  const context=vm.createContext({passwordAuth,authMessage,entryMode,catalogPlan,newestFirst,seriesGroups,mergeCatalog,localCover,URLSearchParams,createClient:()=>db,
    sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    fetch:async()=>({ok:true,json:async()=>({openSignup:true,profileMode:'minimal'})}),
    document:{createElement:tag=>node(tag+Math.random()),getElementById:node,querySelectorAll:()=>[],addEventListener(){},visibilityState:'visible'},
    window:{location:{search:'?entry=login'},scrollY:0,scrollTo(){}},setInterval(){},Date,Set,URL,
    FormData:class{constructor(form){this.form=form;}get(k){return this.form.elements[k]?.value;}},
  });
  await vm.runInContext(`(async()=>{${source}\n})()`,context);
  async function flush(){for(let i=0;i<20;i++)await Promise.resolve();}
  async function click(id){await node(id).onclick();await flush();}
  async function submit(id,values){for(const [k,v] of Object.entries(values)) node(id).elements[k].value=v;node(id).onsubmit({preventDefault(){},target:node(id),submitter:node(id+'-submit')});await flush();}
  return {node,calls,storage,click,submit};
}
test('app password login skips OTP and never changes membership',async()=>{
  const h=await harness();
  await h.submit('login-form',{email:'member@example.invalid',password:'test-password-only'});
  assert.equal(h.calls.filter(x=>x[0]==='login').length,1);
  assert.equal(h.calls.filter(x=>x[0]==='code').length,0);
  assert.equal(h.node('membership').hidden,false);
  assert.equal(h.node('catalog-panel').hidden,false);
  assert.equal(h.node('admin-panel').hidden,true);
});
test('first signup: OTP then password then profile, with no password in browser storage',async()=>{
  const h=await harness({hasProfile:false});
  await h.click('signup-tab');
  await h.submit('login-form',{email:'member@example.invalid'});
  assert.equal(h.calls.find(x=>x[0]==='code')[1].options.shouldCreateUser,true);
  assert.equal(h.node('otp-panel').hidden,false);
  await h.submit('otp-form',{token:'123456'});
  assert.equal(h.node('password-panel').hidden,false);
  assert.equal(h.node('membership').hidden,true);
  assert.equal(h.calls.filter(x=>x[0]==='rpc' && x[1]!=='somnium_public_catalog').length,0);
  await h.submit('password-form',{password:'test-password-only',confirmation:'test-password-only'});
  assert.equal(h.calls.filter(x=>x[0]==='password').length,1);
  assert.equal(h.storage.size,0);
  assert.equal(h.node('password-panel').hidden,true);
  assert.equal(h.node('profile-panel').hidden,false);
});
test('existing member can request setup without signup or entering old password',async()=>{
  const h=await harness();h.node('login-form').elements.email.value='member@example.invalid';
  await h.click('password-help');
  assert.equal(h.calls.find(x=>x[0]==='code')[1].options.shouldCreateUser,false);
  assert.equal(h.node('otp-panel').hidden,false);
});
test('invalid OTP cannot reach password setup',async()=>{
  const h=await harness({verifyError:{code:'otp_expired'}});
  await h.submit('otp-form',{token:'000000'});
  assert.equal(h.node('password-panel').hidden,true);
  assert.equal(h.storage.size,0);
  assert.match(h.node('notice').textContent,/만료/);
});
test('reload during setup keeps password step; cancellation clears marker and signs out',async()=>{
  const h=await harness({existing:true,pending:true});
  assert.equal(h.node('password-panel').hidden,false);
  assert.equal(h.node('membership').hidden,true);
  await h.click('password-cancel');
  assert.equal(h.storage.size,0);
  assert.equal(h.node('password-panel').hidden,true);
  assert.equal(h.node('entry').hidden,false);
});
