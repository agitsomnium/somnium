import {seriesGroups} from './series.js';
import {createClient} from '@supabase/supabase-js';
import {newestFirst} from './order.js';
import {localCover} from './publicCatalog.js';
const $=id=>document.getElementById(id);
const el=(tag,value,parent)=>{const e=document.createElement(tag);if(value)e.textContent=value;parent?.append(e);return e;};
function cover(row,parent){
  const box=el('div','',parent);box.className='lesson-cover';box.setAttribute('aria-hidden','true');
  el('span',row.series_title||'솜니움 회원 강의',box);el('strong',row.title,box);
  if(!localCover(row.thumbnail_url))return;
  const image=el('img','',box);image.alt='';image.width=320;image.height=180;image.loading='lazy';
  image.onerror=()=>{image.remove();box.classList.remove('has-thumbnail');};
  box.classList.add('has-thumbnail');image.src=row.thumbnail_url;
}
function card(row,parent){
  const item=el('article','',parent);item.className='catalog-row';cover(row,item);
  const info=el('div','',item);const date=el('time',row.lecture_date?.replaceAll('-','.')||'',info);date.dateTime=row.lecture_date||'';date.className='lesson-date';el('h3',row.title,info);el('p',row.description,info).className='lesson-description';
  const link=el('a','강의 보기',item);link.className='catalog-open';link.href='/?lesson='+encodeURIComponent(row.id)+'#catalog-panel';
}
let rows=[];
function render(){
  const q=$('browse-search').value.trim().toLowerCase();
  const found=rows.filter(r=>(r.title+' '+r.series_title+' '+r.description).toLowerCase().includes(q));
  $('browse-list').replaceChildren();$('browse-count').textContent=`강의 ${rows.length}편 · 검색 결과 ${found.length}편`;
  for(const group of seriesGroups(found)){
    if(!group.bundled){card(group.lessons[0],$('browse-list'));continue;}
    const details=el('details','',$('browse-list'));details.className='series-group';details.open=!!q;
    const summary=el('summary','',details);cover(group.lessons[0],summary);
    const label=el('div','',summary);el('h3',group.name,label);el('p',`${group.lessons.length}개 강의 · 눌러서 펼쳐보기`,label);
    const body=el('div','',details);body.className='series-lessons';for(const row of group.lessons)card(row,body);
  }
}
$('browse-search').oninput=render;
try{
  const config=await fetch('/runtime-config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();});
  // No login/session needed for this public metadata endpoint.
  const client=createClient(config.url,config.publishableKey,{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
  const {data,error}=await client.rpc('somnium_public_catalog');if(error)throw error;
  rows=newestFirst(data);render();
}catch{
  $('browse-count').textContent='강의 목록을 불러오지 못했습니다. 잠시 후 다시 열어 주세요.';
}
