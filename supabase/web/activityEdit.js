// Apply an administrator's text edits to a stored activity paper without touching its fixed template.
// Only assessment lines and the two channel summary lines can change; counts, money and structure cannot.
const OPEN='<script id="report-data" type="application/json">',CLOSE='</script>',VERSION='somnium-activity-paper/1';
const CONTACT=/01[016789][- ]?\d{3,4}[- ]?\d{4}|[\w.+-]+@[\w-]+\.[\w.]+/;
export const isActivityPaper=body=>typeof body==='string'&&body.includes(OPEN)&&body.includes(VERSION);
export function applyActivityEdits(body,edits){
  if(!isActivityPaper(body))throw Error('활동보고서만 이 화면에서 고칠 수 있습니다.');
  const a=body.indexOf(OPEN)+OPEN.length,b=body.indexOf(CLOSE,a);
  if(b<0||body.indexOf(OPEN,a)>=0)throw Error('보고서 형식을 읽지 못했습니다.');
  const data=JSON.parse(body.slice(a,b));
  if(data.version!==VERSION||!Array.isArray(data.programs))throw Error('보고서 형식을 읽지 못했습니다.');
  if(!edits||typeof edits!=='object')throw Error('고친 내용이 없습니다.');
  const text=(v,max)=>{if(typeof v!=='string'||v.length>max)throw Error('입력이 너무 깁니다.');if(CONTACT.test(v))throw Error('전화번호나 이메일은 보고서에 넣지 않습니다.');return v.trim();};
  for(const [key,lines] of Object.entries(edits.assess||{})){
    const program=data.programs[Number(key)];
    if(!/^\d+$/.test(key)||!program||!Array.isArray(lines)||lines.length>20)throw Error('평가 입력을 확인해 주세요.');
    program.assess=lines.map(line=>text(line,600)).filter(Boolean);
  }
  for(const [key,meta] of Object.entries(edits.channels||{})){
    if(!['youtube','instagram'].includes(key)||!data.channels||!data.channels[key])throw Error('채널 입력을 확인해 주세요.');
    data.channels[key].meta=text(meta,300);
  }
  const encoded=JSON.stringify(data).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
  return body.slice(0,a)+encoded+body.slice(b);
}
