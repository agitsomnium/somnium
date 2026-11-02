import {downloadReport} from './reportDownload.js';
export function accounting(db,{access,rpc,notice}) {
  const $=id=>document.getElementById(id);
  let signature='';
  const text=(tag,value,parent)=>{const e=document.createElement(tag);e.textContent=value;parent.append(e);return e;};
  async function run(button,fn){button.disabled=true;try{await fn();}catch(e){notice(e.message);}finally{button.disabled=false;}}
  function clear(){signature='';$('report-list').replaceChildren();$('report-upload').hidden=true;$('report-login').hidden=false;$('report-status').textContent='회계 보고서는 로그인한 회원에게 공개합니다.';}
  async function load(){
    const start={...access()};
    if(!start.member){clear();return;}
    const rows=await rpc('reports'),now=access();
    if(start.userId!==now.userId || start.epoch!==now.epoch || !now.member)return;
    $('report-login').hidden=true;$('report-upload').hidden=!now.admin;
    $('report-status').textContent=rows.length?`회계 보고서 ${rows.length}건`:'등록된 보고서가 없습니다. 정리된 보고서가 올라오면 이곳에서 볼 수 있습니다.';
    const next=JSON.stringify([now.userId,now.admin,rows]);if(next===signature)return;signature=next;
    $('report-list').replaceChildren();
    for(const report of rows){
      const row=text('article','',$('report-list'));row.className='report-row';
      text('h3',report.title,row);text('p',[report.period,report.enabled?'회원 공개':'숨김'].filter(Boolean).join(' · '),row);
      const button=text('button','PDF 내려받기',row);button.type='button';
      button.onclick=()=>run(button,async()=>{
        const offered=await downloadReport(report,{
          access,list:()=>rpc('reports'),
          download:async path=>{const {data,error}=await db.storage.from('somnium-accounting').download(path,{}, {cache:'no-store'});if(error)throw Error('보고서를 받지 못했습니다. 로그인 상태를 확인해 주세요.');return data;},
          offer:(blob,filename)=>{const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);},
        });notice(offered?'보고서 내려받기를 시작했습니다.':'이용 상태가 바뀌어 내려받기를 중단했습니다.');
      });
      if(now.admin){
        const toggle=text('button',report.enabled?'회원 목록에서 숨기기':'회원 목록에 표시',row);toggle.type='button';
        toggle.onclick=()=>run(toggle,async()=>{await rpc('set_report',{p_id:report.id,p_enabled:!report.enabled});await load();});
      }
    }
  }
  $('report-form').onsubmit=e=>{
    e.preventDefault();const form=e.target,f=new FormData(form),button=e.submitter;
    run(button,async()=>{
      const start={...access()};if(!start.admin)throw Error('관리자만 보고서를 올릴 수 있습니다.');
      const file=f.get('file');
      if(!(file instanceof File) || !file.size || file.size>25*1024*1024 || !file.name.toLowerCase().endsWith('.pdf') || await file.slice(0,5).text()!=='%PDF-')throw Error('25MB 이하의 PDF 파일을 선택해 주세요.');
      const path=crypto.randomUUID()+'.pdf';
      const {error}=await db.storage.from('somnium-accounting').upload(path,file,{contentType:'application/pdf',upsert:false,cacheControl:'0'});
      if(error)throw Error('업로드하지 못했습니다. 관리자 권한과 연결 상태를 확인해 주세요.');
      const end=access();if(start.userId!==end.userId || start.epoch!==end.epoch || !end.admin)throw Error('계정 상태가 바뀌어 등록을 중단했습니다.');
      await rpc('save_report',{p_title:String(f.get('title')).trim(),p_period:String(f.get('period')||'').trim(),p_filename:file.name,p_path:path,p_enabled:f.get('published')==='on'});
      form.reset();await load();notice(f.get('published')==='on'?'회계 보고서를 올렸습니다. 로그인한 회원이 볼 수 있습니다.':'보고서를 임시 저장했습니다. 아직 관리자만 볼 수 있습니다.');
    });
  };
  return {load,clear};
}
