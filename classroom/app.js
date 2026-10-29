'use strict';
const el = id => document.getElementById(id);
let current = null, challenge = '';
const statusNames = {pending:'승인 대기',approved:'승인',held:'보류',suspended:'이용 중지'};
async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,csrf:current?.csrf})};
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '처리하지 못했습니다.');
  return result;
}
function node(tag, text, parent) {const n=document.createElement(tag); if(text)n.textContent=text; if(parent)parent.append(n); return n;}
function notice(text){el('notice').textContent=text;}
function submit(id, fn){el(id).addEventListener('submit',async event=>{
  event.preventDefault(); const button=event.submitter; button.disabled=true;
  try{await fn(new FormData(event.target));}catch(error){notice(error.message);}finally{button.disabled=false;}
});}
function startVerify(result){challenge=result.challenge;el('entry').hidden=true;el('verification').hidden=false;el('mail-code').textContent='';el('verify').reset();el('verify').elements.code.focus();notice('시험 인증번호를 준비했습니다.');}
submit('apply',async f=>{startVerify(await api('/api/apply',{name:f.get('name'),birth:f.get('birth'),phone:f.get('phone'),email:f.get('email'),consent:f.get('consent')==='on'}));});
submit('login',async f=>{startVerify(await api('/api/otp',{email:f.get('email')}));});
el('mail').onclick=async()=>{try{const mail=await api('/api/test-mail',{challenge});el('mail-code').textContent=`가상 수신자 ${mail.email} · 시험 인증번호 ${mail.code} · 유효시간 5분`; }catch(e){notice(e.message);}};
submit('verify',async f=>{const r=await api('/api/verify',{challenge,code:f.get('code')});challenge='';el('verification').hidden=true;el('mail-code').textContent='';await refresh();notice(r.message);});
el('logout').onclick=async()=>{try{await api('/api/logout',{});await refresh();notice('로그아웃했습니다.');}catch(e){notice(e.message);}};
el('theme').onclick=()=>{document.body.classList.toggle('theme-a');el('theme').textContent=document.body.classList.contains('theme-a')?'밝게 보기':'어둡게 보기';};
async function refresh(){
  current=(await api('/api/me')).member;
  el('entry').hidden=!!current;el('logout').hidden=!current;el('classroom').hidden=!current;el('admin').hidden=current?.role!=='admin';
  el('lessons').replaceChildren();el('members').replaceChildren();el('audit').replaceChildren();
  if(!current)return;
  el('identity').textContent=`${current.name} · ${current.email} · ${statusNames[current.status]}`;
  try{const lessons=await api('/api/lessons');if(!lessons.length)node('p','등록된 강의가 없습니다.',el('lessons'));
    for(const lesson of lessons){const article=node('article','',el('lessons'));article.className='lesson';node('h3',lesson.title,article);
      const video=node('video','',article);video.controls=true;video.playsInline=true;video.preload='metadata';video.src=`/media/${lesson.id}/video`;
      const link=node('a','자료 내려받기',article);link.href=`/media/${lesson.id}/material`;link.download='somnium-trial-notes.txt';}}
  catch(e){notice(e.message);}
  if(current.role!=='admin')return;
  const members=await api('/api/admin/members');
  if(!members.length)node('p','아직 가입 신청이 없습니다.',el('members'));
  for(const m of members){const row=node('article','',el('members'));row.className='member';node('h3',`${m.name} · ${statusNames[m.status]}`,row);node('p',`${m.email} / ${m.birth} / ${m.phone}`,row);node('p',`이메일 ${m.verified?'확인됨':'미확인'} · 동의 ${m.consent_version}`,row);
    const label=node('label','',row);label.className='check';const matched=node('input','',label);matched.type='checkbox';node('span','한빛누리 후원 내역을 수동 대조했습니다.',label);
    const actions=node('div','',row);actions.className='actions';
    for(const state of ['approved','held','suspended']){const b=node('button',statusNames[state],actions);b.disabled=state==='approved'&&!m.verified;b.onclick=async()=>{b.disabled=true;try{await api('/api/admin/status',{email:m.email,status:state,matched:matched.checked});await refresh();notice('회원 상태를 변경했습니다.');}catch(e){notice(e.message);b.disabled=false;}};}}
  for(const a of await api('/api/admin/audit'))node('p',`${new Date(a.at*1000).toLocaleString('ko-KR')} · ${a.actor} · ${a.action} · ${a.target}`,el('audit'));
}
submit('upload',async f=>{const file=f.get('video');if(file.size>10000000)throw new Error('10MB 이하 시험 영상만 올릴 수 있습니다.');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));await api('/api/admin/lessons',{title:f.get('title'),audience:f.get('audience'),video:btoa(binary),material:f.get('material')});el('upload').reset();await refresh();notice('시험 강의와 자료를 등록했습니다.');});
// Recheck rights on return; media byte/range requests always check the current database state.
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh().catch(e=>notice(e.message));});
refresh().catch(e=>notice(e.message));
