export async function downloadReport(report, {access,list,download,offer}) {
  const start={...access()};
  if(!start.userId || !start.member) throw Error('로그인한 회원만 회계 보고서를 볼 수 있습니다.');
  const contains=rows=>rows.some(r=>r.id===report.id && r.path===report.path);
  if(!contains(await list())) throw Error('현재 열람할 수 없는 보고서입니다.');
  const blob=await download(report.path);
  const rows=await list();
  const end=access();
  if(!end.member || start.userId!==end.userId || start.epoch!==end.epoch || !contains(rows)) return false;
  return (await offer(blob,report.filename))!==false;
}
