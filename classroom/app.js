"use strict";
const el = id => document.getElementById(id);
let current = null, challenge = '', verificationRequest = null, view = 'catalog';
let features = {purchases:false};
let catalog = [], ownOrders = [], adminMembers = [], adminOrders = [], adminLessons = [], playingId = '';
const states = {pending:'승인 대기', approved:'이용 가능', held:'보류', suspended:'계정 중지'};
const reviewStates = {not_requested:'후원 신청 없음', pending:'후원 확인 대기', qualified:'후원 자격 확인됨', held:'후원 심사 보류', withdrawn:'후원 자격 종료'};
const orderStates = {awaiting:'입금 확인 대기', confirmed:'수강권 부여 완료', cancelled:'취소·수강권 회수'};
const eraNames = {archive:'이전 강의 · 회원 전용', current:'현대 자본주의', future:'2027 신규 강좌'};
const auditActions = {supporter_requested:'후원 확인 요청',director_granted:'이사 자격 승인',director_revoked:'이사 자격 종료',account_approved:'계정 이용 재개', account_suspended:'계정 이용 중지', supporter_qualified:'후원 자격 승인', supporter_held:'후원 심사 보류', supporter_withdrawn:'후원 자격 종료', order_confirmed:'시험 입금 확인·수강권 부여', order_cancelled:'신청 취소·수강권 회수', lesson_created:'강의 등록', lesson_updated:'강의 소개 수정', lesson_hidden:'강의 숨김', lesson_published:'강의 표시', approved:'이전 방식 승인', held:'이전 방식 보류', suspended:'이전 방식 중지'};
function node(tag, text, parent) {
  const n = document.createElement(tag);
  if (text) n.textContent = text;
  if (parent) parent.append(n);
  return n;
}
function notice(text) { el('notice').textContent = text; }
function button(text, parent, fn) {
  const b = node('button', text, parent); b.type = 'button';
  b.onclick = async () => {
    b.disabled = true;
    try { await fn(); } catch (e) { notice(e.message); }
    finally { b.disabled = false; }
  };
  return b;
}
function badge(text, parent) { node('span', text, parent).className = 'status-badge'; }
function when(value) { return new Date(value * 1000).toLocaleString('ko-KR'); }
function ask(title, text) {
  el('confirm-title').textContent = title;
  el('confirm-body').textContent = text;
  el('confirm-dialog').showModal();
  return new Promise(resolve => {
    const finish = value => { el('confirm-dialog').close(); resolve(value); };
    el('confirm-yes').onclick = () => finish(true);
    el('confirm-no').onclick = () => finish(false);
    el('confirm-dialog').oncancel = e => { e.preventDefault(); finish(false); };
    el('confirm-no').focus();
  });
}
async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({...data, csrf:current?.csrf})};
  const r = await fetch(path, options);
  const v = await r.json();
  if (!r.ok) throw new Error(v.error || '처리하지 못했습니다.');
  return v;
}
function submit(id, fn) {
  el(id).addEventListener('submit', async e => {
    e.preventDefault(); const b = e.submitter; b.disabled = true;
    try { await fn(new FormData(e.target)); } catch (x) { notice(x.message); }
    finally { b.disabled = false; }
  });
}
function selectView(name) {
  if (!['catalog','guide'].includes(name) && !current) { notice('먼저 이메일로 로그인해 주세요.'); entryMode('login'); return; }
  if (name === 'admin' && current?.role !== 'admin') return;
  view = name;
  el('entry').hidden = !!current || !!challenge || name === 'guide';
  for (const v of ['catalog','guide','mine','admin']) el(v+'-view').hidden = v !== name;
  document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-current', b.dataset.view === name ? 'page' : 'false'));
  if (name !== 'mine') { document.querySelector('video')?.pause(); if (el('player-region').querySelector('iframe')) { el('player-region').replaceChildren(); playingId=''; } }
}
function entryMode(mode) {
  el('apply-section').hidden = mode !== 'apply'; el('login-section').hidden = mode !== 'login';
  document.querySelectorAll('[data-entry]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.entry === mode)));
}
for (const b of document.querySelectorAll('[data-view]')) b.onclick = () => selectView(b.dataset.view);
for (const b of document.querySelectorAll('[data-entry]')) b.onclick = () => entryMode(b.dataset.entry);
for (const b of document.querySelectorAll('[data-admin]')) b.onclick = () => {
  for (const v of ['members','orders','upload','accounting']) el(v === 'orders' ? 'admin-orders-panel' : v+'-panel').hidden = v !== b.dataset.admin;
  document.querySelectorAll('[data-admin]').forEach(t => t.setAttribute('aria-pressed', String(t === b)));
};
for (const b of document.querySelectorAll('[data-email]')) b.onclick = () => {
  entryMode('login'); el('login').elements.email.value = b.dataset.email;
  el('login').elements.email.focus(); notice('인증번호 받기를 누른 뒤 시험 메일함을 확인해 주세요.');
};
el('refresh').onclick = async () => { try { await refresh(); notice('최신 이용 상태를 불러왔습니다.'); } catch(e) { notice(e.message); } };
el('theme').onclick = () => { document.body.classList.toggle('theme-a'); el('theme').textContent = document.body.classList.contains('theme-a') ? '밝게' : '어둡게'; };
function startVerify(result) {
  challenge = result.challenge; el('entry').hidden = true; el('verification').hidden = false;
  el('mail-code').textContent = ''; el('verify').reset(); el('verify').elements.code.focus();
  notice('실제 발송 없이 시험 인증번호를 준비했습니다.');
}
submit('apply', async f => { verificationRequest = {email:f.get('email'), purpose:'verify'}; startVerify(await api('/api/apply',{...Object.fromEntries(f), consent:f.get('consent') === 'on'})); });
submit('login', async f => { verificationRequest = {email:f.get('email'), purpose:'login'}; startVerify(await api('/api/otp',{email:f.get('email')})); });
el('resume-verification').onclick = async () => {
  try { verificationRequest = {email:el('login').elements.email.value, purpose:'verify'}; startVerify(await api('/api/resend-verification',{email:verificationRequest.email})); } catch(e) { notice(e.message); }
};
el('resend').onclick = async () => {
  try { if (!verificationRequest) return; startVerify(await api(verificationRequest.purpose === 'login' ? '/api/otp' : '/api/resend-verification',{email:verificationRequest.email})); notice('새 인증번호를 준비했습니다. 이전 번호는 사용할 수 없습니다.'); } catch(e) { notice(e.message); }
};
el('mail').onclick = async () => {
  try { const m = await api('/api/test-mail',{challenge}); el('mail-code').textContent = `가상 수신자 ${m.email} · 시험 인증번호 ${m.code} · 유효시간 5분`; } catch(e) { notice(e.message); }
};
el('back-login').onclick = () => { challenge = ''; el('verification').hidden = true; el('entry').hidden = false; el('mail-code').textContent = ''; };
submit('verify', async f => {
  const r = await api('/api/verify',{challenge, code:f.get('code')}); challenge = '';
  el('verification').hidden = true; el('mail-code').textContent = ''; await refresh(true); notice(r.message);
});
el('logout').onclick = async () => { try { await api('/api/logout',{}); view = 'catalog'; await refresh(); notice('로그아웃했습니다.'); } catch(e) { notice(e.message); } };
function seriesName(id) { const l = catalog.find(l => l.series_id === id); return l?.series_title || l?.title.split('·')[0].trim() || '시리즈 강좌'; }
function targetName(o) { return o.target_label || (o.target_type === 'series' ? `시리즈 · ${seriesName(o.target_id)}` : catalog.find(l => l.id === o.target_id)?.title || '등록 강좌'); }
function capturedList(o, parent) {
  const d = node('details','',parent); node('summary',`신청 당시 포함 강의 ${o.lessons.length}개`,d);
  const list = node('ol','',d); for (const l of o.lessons) node('li',l.title,list);
}
async function order(kind, id) {
  if (!features.purchases) { notice('현재는 후원회원·이사 강의실을 운영합니다.'); return; }
  if (!current) { entryMode('apply'); el('apply').elements.intent.value = 'purchase'; notice('구매 신청으로 가입·이메일 확인 후 로그인해 주세요.'); el('entry').scrollIntoView({block:'start'}); return; }
  const lessons = catalog.filter(l => kind === 'lesson' ? l.id === id : l.series_id === id);
  if (!await ask('시험 구매 신청 확인', `${kind === 'series' ? seriesName(id) : lessons[0]?.title}\n포함 강의 ${lessons.length}개\n${lessons.map(l => l.title).join('\n')}\n\n실제 입금하지 마세요. 신청만으로 강의가 열리지 않습니다. 시리즈 범위는 신청 당시 강의로 고정하는 시험안입니다.`)) return;
  const r = await api('/api/orders',{target_type:kind, target_id:id}); await refresh(); selectView('mine');
  notice(r.duplicate ? '이미 같은 시험 신청이 있습니다.' : '시험 신청을 접수했습니다. 관리자 입금 확인 후 수강권이 열립니다. 실제 입금하지 마세요.');
}
function lessonRow(l, parent) {
  const row = node('article','',parent); row.className = 'catalog-row';
  const cover = node('div','',row); cover.className='lesson-cover'; cover.setAttribute('aria-hidden','true'); node('span',l.series_title || 'SOMNIUM · 회원 강의',cover); node('strong',l.title.split('·').slice(-1)[0].trim(),cover); node('span','솜니움 기독교정치사회연구소',cover);
  const text = node('div','',row); node('h3',l.title,text);
  if (l.description) node('p',l.description,text).className = 'lesson-description';
  node('p',features.purchases ? (l.era === 'archive' ? '후원회원·이사 전용' : '후원회원·이사는 추가 구매 없이 이용') : '후원 확인을 마친 회원이 이용할 수 있습니다.',text).className = 'muted';
  const actions = node('div','',row); actions.className = 'row-actions';
  if (l.accessible) button('강의 보기',actions,async () => { selectView('mine'); showPlayer(l.id); });
  else {
    const pending = ownOrders.some(o => o.status === 'awaiting' && o.lessons.some(i => i.lesson_id === l.id));
    badge(pending ? '입금 확인 대기' : '승인 후 이용',actions);
    if (features.purchases && l.purchasable && !pending) button('단강좌 시험 신청',actions,() => order('lesson',l.id));
  }
}
function renderCatalog() {
  el('catalog').replaceChildren(); const q = el('catalog-search').value.trim().toLowerCase();
  const filtered = catalog.filter(l => `${l.title} ${l.description} ${l.series_title}`.toLowerCase().includes(q));
  el('catalog-count').textContent = `등록 강의 ${catalog.length}개 · 검색 결과 ${filtered.length}개`;
  for (const era of ['archive','current','future']) {
    const list = filtered.filter(l => l.era === era); if (!list.length) continue;
    const group = node('div','',el('catalog')); group.className = 'catalog-group'; node('h3',eraNames[era],group).className = 'group-title';
    for (const l of list) lessonRow(l,group);
    for (const id of new Set(list.map(l => l.series_id).filter(Boolean))) {
      const full = catalog.filter(l => l.series_id === id);
      if (!features.purchases || era === 'archive' || full.every(l => l.accessible)) continue;
      const bar = node('div','',group); bar.className = 'series-bar';
      node('p',`${seriesName(id)} · 현재 포함 강의 ${full.length}개`,bar);
      const pending = ownOrders.some(o => o.target_type === 'series' && o.target_id === id && o.status === 'awaiting');
      if (pending) badge('시리즈 입금 확인 대기',bar);
      else button('시리즈 전체 시험 신청',bar,() => order('series',id));
    }
  }
  if (!filtered.length) node('p',q ? '검색한 강의가 없습니다. 다른 검색어를 입력해 주세요.' : (current ? '현재 이용 가능한 강의가 없습니다. 후원하셨다면 나의 강의실에서 확인을 요청해 주세요.' : '로그인 후 이용 가능한 강의를 확인해 주세요.'),el('catalog'));
}
el('catalog-search').oninput = renderCatalog;
async function showPlayer(id) {
  const viewer=current?.email;
  let playback;
  try { playback=await api(`/api/player/${id}`); } catch(e) { el('player-region').replaceChildren(); playingId=''; notice(e.message); return; }
  const l = catalog.find(l => l.id === id); if (view!=='mine' || !viewer || current?.email!==viewer || !l?.accessible) { notice('이용 권한이 없습니다.'); return; }
  if (playingId !== id || !el('player-region').firstChild) {
    playingId = id; el('player-region').replaceChildren();
    const box = node('article','',el('player-region')); box.id = 'player'; node('h3',l.title,box);
    if (l.description) node('p',l.description,box);
    if (playback.provider==='mp4') {
      const v = node('video','',box); v.controls=true; v.playsInline=true; v.preload='metadata'; v.src=playback.url;
      v.onerror=()=>notice('영상을 불러오지 못했습니다. 이용 상태를 새로고침하거나 관리자에게 확인해 주세요.');
    } else {
      const v=node('iframe','',box); v.className='member-player'; v.title=l.title; v.src=playback.url; v.allow='encrypted-media; fullscreen; picture-in-picture'; v.allowFullscreen=true; v.referrerPolicy='strict-origin-when-cross-origin';
      node('p',playback.provider==='youtube' ? '일부공개 유튜브 영상입니다. 회원을 위한 강의 링크를 외부에 공유하지 말아 주세요.' : '영상이 열리지 않으면 관리자에게 재생 허용 도메인 설정을 확인해 주세요.',box).className='member-player-note';
    }
    if (l.material_ready) { const a = node('a','자료 내려받기',box); a.href = `/media/${id}/material`; a.download = 'somnium-notes.txt'; } else node('p','강의 자료는 준비 중입니다.',box).className='muted';
    const next = catalog.filter(r => r.accessible && r.series_id && r.series_id === l.series_id);
    const at = next.findIndex(r => r.id === id);
    if (at+1 < next.length && at >= 0) button('다음 강의',box,() => showPlayer(next[at+1].id));
  }
  el('player-region').scrollIntoView({block:'nearest'});
}
function renderMine(messages) {
  for (const id of ['lessons','orders','notifications']) el(id).replaceChildren();
  el('identity').textContent = `${current.name} · ${current.director || current.supporter ? '회원 강의 이용 가능' : current.supporter_review === 'not_requested' ? '일반회원' : reviewStates[current.supporter_review]} · ${states[current.status]}`;
  el('supporter-request-panel').hidden = current.role === 'admin' || current.supporter || current.director;
  el('supporter-request').disabled = current.supporter_review === 'pending';
  el('supporter-request').textContent = current.supporter_review === 'pending' ? '후원 확인 대기 중' : '후원 확인 요청';
  const available = catalog.filter(l => l.accessible);
  el('mine-summary').textContent = `이용 가능 ${available.length}강` + (features.purchases ? ` · 입금 확인 대기 ${ownOrders.filter(o => o.status === 'awaiting').length}건` : ' · 비공개 회원 강의');
  if (!available.length) node('p','아직 이용 가능한 회원 강의가 없습니다. 후원하셨다면 확인을 요청해 주세요.',el('lessons'));
  for (const l of available) { const row = node('div','',el('lessons')); row.className = 'owned-row'; node('span',l.title,row); button('재생·자료',row,() => showPlayer(l.id)); }
  if (!ownOrders.length) node('p','구매 신청 내역이 없습니다. 후원회원은 추가 구매가 필요하지 않습니다.',el('orders'));
  for (const o of ownOrders) {
    const row = node('article','',el('orders')); row.className = 'order-row'; node('h3',targetName(o),row); badge(orderStates[o.status],row);
    node('p',`시험 신청일 ${when(o.created_at)}`,row).className = 'muted'; capturedList(o,row);
    if (o.status === 'awaiting') button('신청 취소',row,async () => { if (!await ask('시험 신청을 취소할까요?',targetName(o))) return; await api('/api/orders/cancel',{id:o.id}); await refresh(); notice('대기 신청을 취소했습니다.'); });
  }
  if (!messages.length) node('p','수강권이 열리면 시험 안내 내용이 표시됩니다.',el('notifications'));
  for (const n of messages) node('p',n.body,el('notifications'));
}
function matches(value, q) { return value.toLowerCase().includes(q.trim().toLowerCase()); }
function renderMembers() {
  el('members').replaceChildren(); const q = el('member-search').value, filter = el('member-filter').value;
  const rows = adminMembers.filter(m => matches(`${m.name} ${m.email}`,q) && (filter === 'all' || (filter === 'director' ? m.director : filter === 'director_pending' ? m.audience === 'director' && !m.director : filter === 'suspended' ? m.status === filter : m.supporter_review === filter)));
  el('member-count').textContent = `${rows.length}명 / 전체 ${adminMembers.length}명`;
  if (!rows.length) node('p','조건에 맞는 회원이 없습니다.',el('members'));
  for (const m of rows) {
    const row = node('article','',el('members')); row.className = 'member'; node('h3',m.name,row); badge(states[m.status],row); if (m.director) badge('이사 자격 확인됨',row); else if (m.audience === 'director') badge('이사 확인 대기',row); badge(reviewStates[m.supporter_review] || '후원 확인 대기',row);
    node('p',`${m.email} / ${m.birth} / ${m.phone} · 이메일 ${m.verified ? '확인됨' : '미확인'}`,row).className = 'member-contact';
    const label = node('label','',row); label.className = 'check'; const check = node('input','',label); check.type = 'checkbox'; node('span','한빛누리에서 월 1만 원 이상 후원을 확인했습니다.',label);
    const rosterLabel = node('label','',row); rosterLabel.className = 'check'; const roster = node('input','',rosterLabel); roster.type = 'checkbox'; node('span','이사 명단에서 대상자를 확인했습니다.',rosterLabel);
    const actions = node('div','',row); actions.className = 'actions';
    const directorButton = button(m.director ? '이사 자격 종료' : '이사 자격 승인',actions,async () => {
      if (!m.director && !roster.checked) { notice('이사 명단 확인란을 먼저 체크해 주세요.'); return; }
      if (!await ask(m.director ? '이사 자격을 종료할까요?' : '이사 자격을 승인할까요?',`${m.name} · ${m.email}\n${m.director ? '이사 자격으로 열리던 강의를 제한합니다. 별도 후원 자격은 유지됩니다.' : '후원 금액과 관계없이 모든 회원 강의를 이용합니다. 운영관리·회계 열람 권한은 부여하지 않습니다.'}`)) return;
      const r = await api('/api/admin/director',{email:m.email,enabled:!m.director,roster_confirmed:roster.checked}); await refresh(); notice(r.message);
    }); directorButton.disabled = !m.verified;
    const grant = button('후원 자격 승인',actions,async () => { await api('/api/admin/supporter',{email:m.email,qualified:true,minimum_confirmed:check.checked}); await refresh(); notice('후원 자격을 승인했습니다.'); }); grant.disabled = !m.verified;
    for (const [text,hold] of [['후원 심사 보류',true],['후원 자격 종료',false]]) button(text,actions,async () => {
      if (!await ask(text,`${m.name} · ${m.email}\n후원 자격을 종료합니다. 별도 이사 자격은 유지됩니다.`)) return;
      await api('/api/admin/supporter',{email:m.email,qualified:false,hold}); await refresh(); notice(`${text} 처리했습니다. 별도 이사 자격은 유지됩니다.`);
    });
    button(m.status === 'suspended' ? '계정 이용 재개' : '계정 이용 중지',actions,async () => {
      const status = m.status === 'suspended' ? 'approved' : 'suspended';
      if (!await ask(status === 'suspended' ? '모든 강의 이용을 중지할까요?' : '계정 이용을 재개할까요?',`${m.name} · ${m.email}\n${status === 'suspended' ? '모든 회원 강의를 차단하고 로그인 상태를 해제합니다.' : '후원·이사 자격은 별도로 적용됩니다.'}`)) return;
      await api('/api/admin/account',{email:m.email,status}); await refresh(); notice('계정 이용 상태를 변경했습니다.');
    });
  }
}
function renderOrders() {
  el('admin-orders').replaceChildren(); const q = el('order-search').value, filter = el('order-filter').value;
  const rows = adminOrders.filter(o => matches(`${o.name} ${o.email} ${targetName(o)}`,q) && (filter === 'all' || o.status === filter));
  el('order-count').textContent = `${rows.length}건 / 전체 ${adminOrders.length}건`;
  if (!rows.length) node('p','조건에 맞는 구매 신청이 없습니다.',el('admin-orders'));
  for (const o of rows) {
    const row = node('article','',el('admin-orders')); row.className = 'order-row'; node('h3',targetName(o),row); badge(orderStates[o.status],row);
    node('p',`${o.name} · ${o.email} · ${when(o.created_at)}`,row); capturedList(o,row);
    if (o.status === 'awaiting') {
      const label = node('label','',row); label.className = 'check'; const c = node('input','',label); c.type = 'checkbox'; node('span','가상 신청의 시험 입금 확인을 완료했습니다.',label);
      button('시험 입금 확인·수강권 부여',row,async () => {
        if (!c.checked) { notice('시험 입금 확인란을 먼저 체크해 주세요.'); return; }
        if (!await ask('시험 수강권을 부여할까요?',`${o.name} · ${o.email}\n${targetName(o)}\n신청 당시 포함 강의 ${o.lessons.length}개\n실제 입금·메일 발송은 없습니다.`)) return;
        const r = await api('/api/admin/orders',{id:o.id,status:'confirmed',matched:c.checked}); await refresh(); notice(r.message);
      });
    }
    if (o.status !== 'cancelled') button('신청 취소·수강권 회수',row,async () => {
      if (!await ask('이 신청의 수강권을 회수할까요?',`${o.name} · ${o.email}\n${targetName(o)}\n다른 구매·후원 권한은 유지됩니다. 실제 환불은 처리하지 않습니다.`)) return;
      const r = await api('/api/admin/orders',{id:o.id,status:'cancelled'}); await refresh(); notice(r.message);
    });
  }
}
function renderLessonAdmin() {
  el('admin-lessons').replaceChildren(); const q = el('lesson-search').value;
  for (const l of adminLessons.filter(l => matches(`${l.title} ${l.series_title}`,q))) {
    const row = node('article','',el('admin-lessons')); row.className = 'order-row'; node('h3',l.title,row);
    node('p',`${eraNames[l.era]} · ${l.series_title || '독립 강좌'} · ${l.position}번`,row); badge(l.published ? '회원 목록 표시 중' : '숨김 · 접근 차단',row);
    button(l.published ? '강의 숨기기' : '회원 목록에 표시',row,async () => {
      if (l.published && !await ask('강의를 숨길까요?',`${l.title}\n기존 수강권이 있어도 이 강의의 영상·자료 요청을 차단합니다.`)) return;
      const r = await api('/api/admin/lesson-publication',{id:l.id,published:!l.published}); await refresh(); notice(r.message);
    });
    const edit = node('details','',row); node('summary','제목·소개·순서 수정',edit); const form = node('form','',edit);
    const fields = {};
    for (const [key,text,tag] of [['title','강의 제목','input'],['description','강의 소개','textarea'],['position','표시 순서','input']]) {
      const label = node('label',text,form); const input = node(tag,'',label); input.value = l[key]; fields[key] = input;
      if (key === 'position') { input.type = 'number'; input.min = 1; input.max = 999; } else input.maxLength = key === 'title' ? 100 : 1200;
      input.required = key !== 'description';
    }
    const save = node('button','소개 저장',form); save.type = 'submit';
    form.onsubmit = async e => { e.preventDefault(); save.disabled = true; try { const r = await api('/api/admin/lesson-details',{id:l.id,title:fields.title.value,description:fields.description.value,position:Number(fields.position.value)}); await refresh(); notice(r.message); } catch(e) { notice(e.message); } finally { save.disabled = false; } };
  }
  const select = el('upload').elements.series_id, previous = select.value;
  select.replaceChildren();
  for (const [value,text] of [['','독립 강좌'],['__new','새 시리즈']]) { const option = node('option',text,select); option.value = value; }
  const seen = new Set();
  for (const l of adminLessons) if (l.series_id && !seen.has(l.series_id)) { seen.add(l.series_id); const o = node('option',l.series_title || l.title.split('·')[0].trim(),select); o.value = l.series_id; }
  select.value = [...select.options].some(o => o.value === previous) ? previous : '';
  seriesSelection();
}
function seriesSelection() { const newSeries = el('upload').elements.series_id.value === '__new'; el('new-series-label').hidden = !newSeries; el('upload').elements.series_title.disabled = !newSeries; el('upload').elements.series_title.required = newSeries; }
el('upload').elements.series_id.onchange = seriesSelection;
for (const id of ['member-search','member-filter']) el(id).oninput = renderMembers;
for (const id of ['order-search','order-filter']) el(id).oninput = renderOrders;
el('lesson-search').oninput = renderLessonAdmin;
async function renderAdmin() {
  const results = await Promise.all([api('/api/admin/members'),features.purchases ? api('/api/admin/orders') : Promise.resolve([]),api('/api/admin/lessons'),api('/api/admin/audit'),api('/api/admin/accounting-preview'),api('/api/admin/directors')]);
  el('accounting-status').textContent = results[4].message;
  [adminMembers,adminOrders,adminLessons] = results;
  el('director-roster-list').replaceChildren();
  for (const d of results[5]) {
    const row = node('article','',el('director-roster-list')); row.className = 'order-row'; node('p',`${d.email} · ${d.enabled ? '명단 유효' : '자격 종료'} · ${d.verified ? '이메일 확인 완료' : '가입·이메일 확인 대기'}`,row);
    if (d.enabled) button('명단 적용 해제',row,async () => { if (!await ask('명단 적용을 해제할까요?',d.email)) return; await api('/api/admin/director',{email:d.email,enabled:false}); await refresh(); });
  }
  el('admin-summary').replaceChildren();
  for (const [count,text] of [[adminMembers.filter(m => m.supporter_review === 'pending').length,'후원 확인 대기'],[adminMembers.filter(m => m.director).length,'내부 강의 이용 자격'],[adminMembers.filter(m => m.status === 'suspended').length,'중지 계정'],[adminLessons.filter(l => l.published).length,'표시 중 강의']]) {
    const box = node('div','',el('admin-summary')); node('strong',String(count),box); node('span',text,box);
  }
  renderMembers(); renderOrders(); renderLessonAdmin(); el('audit').replaceChildren();
  for (const a of results[3]) node('p',`${when(a.at)} · ${a.actor} · ${auditActions[a.action] || a.action} · 대상 ${a.target}`,el('audit'));
}
async function refresh(afterLogin = false) {
  features = await api('/api/features');
  document.querySelectorAll('[data-purchase]').forEach(n => n.hidden = !features.purchases);
  current = (await api('/api/me')).member; catalog = await api('/api/catalog');
  document.body.classList.toggle('signed-in-mode',!!current);
  el('entry').hidden = !!current || !!challenge; el('logout').hidden = !current; el('signed-in').hidden = !current;
  el('mine-nav').hidden = !current; el('admin-nav').hidden = current?.role !== 'admin';
  el('signed-in').textContent = current ? `${current.role === 'admin' ? '운영관리자' : '수강자'} · ${current.name} · ${current.email}` : '';
  if (current) {
    const [orders,messages] = features.purchases ? await Promise.all([api('/api/orders'),api('/api/notifications')]) : [[],[]]; ownOrders = orders; renderMine(messages);
    if (current.role === 'admin') await renderAdmin();
    else { adminMembers = []; adminOrders = []; adminLessons = []; for (const id of ['members','admin-orders','audit','admin-lessons','admin-summary','director-roster-list']) el(id).replaceChildren(); }
    if (afterLogin) view = current.role === 'admin' ? 'admin' : 'mine';
  } else {
    el('supporter-request-panel').hidden = true;
    view = ['catalog','guide'].includes(view) ? view : 'catalog'; ownOrders = []; adminMembers = []; adminOrders = []; adminLessons = [];
    for (const id of ['lessons','orders','notifications','members','admin-orders','audit','admin-lessons','admin-summary','director-roster-list','player-region']) el(id).replaceChildren();
  }
  if (!current || !catalog.some(l => l.id === playingId && l.accessible)) { el('player-region').replaceChildren(); playingId = ''; }
  renderCatalog(); selectView(view);
}
submit('director-roster',async f => { const r=await api('/api/admin/director',{email:f.get('email'),enabled:true,roster_confirmed:f.get('roster_confirmed')==='on'}); el('director-roster').reset(); await refresh(); notice(r.message); });
el('supporter-request').onclick=async()=>{try{const r=await api('/api/supporter-request',{});await refresh();notice(r.message);}catch(e){notice(e.message);}};
submit('upload', async f => {
  const file = f.get('video') || new File([], ''); if (file.size > 10000000) throw new Error('10MB 이하 시험 MP4만 등록할 수 있습니다.');
  const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
  for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
  await api('/api/admin/lessons',{title:f.get('title'),era:f.get('era'),series_id:f.get('series_id') === '__new' ? '' : f.get('series_id'),series_title:f.get('series_title') || '',description:f.get('description'),position:Number(f.get('position')),video_provider:f.get('video_provider'),video_url:f.get('video_url') || '',video:btoa(binary),material:f.get('material'),published:f.get('published') === 'on'});
  el('upload').reset(); await refresh(); notice('시험 강의·자료를 등록했습니다. 표시 여부는 등록 강의 관리에서 바꿀 수 있습니다.');
});
document.addEventListener('visibilitychange',() => { if (!document.hidden) refresh().catch(e => notice(e.message)); });
refresh().catch(e => notice(e.message));

// The provider choice changes only metadata; it never changes a provider's privacy settings.
el('upload').elements.video_provider.onchange=()=>{const local=el('upload').elements.video_provider.value==='mp4';el('video-file-field').hidden=!local;el('video-url-field').hidden=local;el('upload').elements.video.required=local;el('upload').elements.video.disabled=!local;el('upload').elements.video_url.required=!local;el('upload').elements.video_url.disabled=local;};
