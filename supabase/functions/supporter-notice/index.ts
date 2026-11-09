import { createClient } from 'npm:@supabase/supabase-js@2.118.0';
import nodemailer from 'npm:nodemailer@10.3.1';

const cors = {'Access-Control-Allow-Origin':'https://somnium-classroom.pages.dev',
 'Access-Control-Allow-Headers':'authorization, apikey, content-type, x-client-info',
 'Access-Control-Allow-Methods':'POST, OPTIONS'};
const response = (data: unknown, status=200) => Response.json(data,{status,headers:cors});
Deno.serve(async(req) => {
 if(req.method==='OPTIONS') return new Response('ok',{headers:cors});
 if(req.method!=='POST') return response({error:'method'},405);
 const jwt=req.headers.get('authorization')?.replace(/^Bearer\s+/i,'');
 if(!jwt) return response({error:'authentication required'},401);
 const db=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  {auth:{persistSession:false,autoRefreshToken:false}});
 const {data:auth,error:authError}=await db.auth.getUser(jwt);
 if(authError||!auth.user) return response({error:'authentication required'},401);
 let target=auth.user.id;
 try {
  const body=await req.json().catch(()=>({}));
  if(body.user_id&&body.user_id!==target){
   const memberClient=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_ANON_KEY')!,
    {global:{headers:{Authorization:'Bearer '+jwt}},auth:{persistSession:false,autoRefreshToken:false}});
   const {data:me,error}=await memberClient.rpc('somnium_me');
   if(error||!me?.admin) return response({error:'admin required'},403);
   target=body.user_id;
  }
  const {data:notice,error}=await db.rpc('somnium_claim_supporter_notice',{p_user:target});
  if(error) return response({error:'queue unavailable'},503);
  if(!notice) return response({queued:false});
  try {
   const transport=nodemailer.createTransport({host:Deno.env.get('NOTICE_SMTP_HOST'),
    port:Number(Deno.env.get('NOTICE_SMTP_PORT')),secure:Deno.env.get('NOTICE_SMTP_PORT')==='465',
    auth:{user:Deno.env.get('NOTICE_SMTP_USER'),pass:Deno.env.get('NOTICE_SMTP_PASSWORD')},
    connectionTimeout:10000,socketTimeout:10000});
   await transport.sendMail({from:{name:'솜니움',address:Deno.env.get('NOTICE_SMTP_FROM')!},
    to:Deno.env.get('NOTICE_TO'),subject:notice.supporter_state==='pending'?'[솜니움] 후원 신청 접수 · 관리자 승인 대기':'[솜니움] 후원회원 신청 알림',
    messageId:`<supporter-${notice.user_id}@somniumagit.com>`,
    text:`${notice.supporter_state==='pending'?'후원 신청을 접수했습니다. 운영자의 확인·승인이 필요합니다.':'후원회원 신청 알림입니다.'}\n\n이름: ${notice.name}\n가입 이메일: ${notice.email}\n신청 시각: ${notice.created_at}\n\n회원·후원 확인 화면에서 신청 내용을 확인하고 후원 신청을 승인해 주세요. 승인 전에는 강의가 열리지 않습니다. 실제 납부 내역은 월별 회계 정리 때 한빛누리 자료와 대조해 주세요. 내역이 맞지 않으면 회원에게 먼저 연락해 주세요.\n\n회원·후원 확인: https://somnium-classroom.pages.dev/#members-admin`});
   const {error:markError}=await db.rpc('somnium_finish_supporter_notice',{p_user:target,p_sent:true});
   return markError?response({error:'delivery status unavailable'},503):response({sent:true});
  }catch(error){
   console.error(JSON.stringify({event:'supporter_mail_failed',name:error?.name,code:error?.code,command:error?.command,responseCode:error?.responseCode}));
   await db.rpc('somnium_finish_supporter_notice',{p_user:target,p_sent:false});
   return response({error:'mail unavailable'},503);
  }
 }catch{return response({error:'request failed'},400);}
});
