import nodemailer from 'nodemailer';
import {randomBytes,randomInt,createHmac,timingSafeEqual} from 'node:crypto';
import {database} from './mongo.mjs';import {accountPrincipal,accountCookie,configured,sameOrigin} from './access.mjs';import {passwordHash} from './accounts.mjs';import {ApiError,fail,fields} from './native/domain.mjs';import {databaseError,repository} from './native/store.mjs';import {connectedPlan} from './native/energy.mjs';
const address=v=>{if(typeof v!=='string'||v.length>254||! /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}$/i.test(v.trim()))fail(422,'Informe um e-mail válido.');return v.trim().toLowerCase();};
const digest=s=>createHmac('sha256',process.env.AETHER_SESSION_SECRET).update(s).digest('hex'),eq=(a,b)=>a?.length===b?.length&&timingSafeEqual(Buffer.from(a),Buffer.from(b));
const mask=email=>email?email.slice(0,2)+'***@'+email.split('@')[1]:null;
const json=(d,status=200,cookie)=>Response.json(d,{status,headers:{'Cache-Control':'no-store',...(cookie?{'Set-Cookie':cookie}:{})}});
export function mailConfigured(){return !!process.env.GMAIL_USER&&(!!process.env.GMAIL_APP_PASSWORD||['GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REFRESH_TOKEN'].every(k=>!!process.env[k]));}
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let transport;
export async function deliverMail({to,subject,text}){if(!mailConfigured())fail(503,'E-mail ainda não ativado pela equipe. Use o código de recuperação salvo.');const user=address(process.env.GMAIL_USER);
 if(!transport){const oauth=['GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REFRESH_TOKEN'].every(k=>!!process.env[k]);transport=nodemailer.createTransport({service:'gmail',auth:oauth?{type:'OAuth2',user,clientId:process.env.GOOGLE_CLIENT_ID,clientSecret:process.env.GOOGLE_CLIENT_SECRET,refreshToken:process.env.GOOGLE_REFRESH_TOKEN}:{user,pass:process.env.GMAIL_APP_PASSWORD.replace(/\s/g,'')},connectionTimeout:10000,greetingTimeout:10000,socketTimeout:20000,disableFileAccess:true,disableUrlAccess:true});}
 const html='<div style="font:16px Arial,sans-serif;background:#080e1c;color:#edf4ff;padding:32px;max-width:620px"><h1 style="color:#71e4d5">Aether AI</h1><p style="white-space:pre-line;line-height:1.7">'+escape(text)+'</p><hr><small>Residência e sensores simulados. Nunca compartilhe senhas ou códigos de recuperação.</small></div>';
 try{const result=await transport.sendMail({from:{name:'Aether AI',address:user},to:address(to),subject,text,html});if(!result.accepted?.length)fail(503,'O Gmail não aceitou a mensagem. Tente novamente mais tarde.');}catch(e){if(e instanceof ApiError)throw e;fail(503,'O envio não foi aceito pelo Gmail. Confira a configuração do remetente ou tente mais tarde.');}
}
async function quota(db,key,max,window=900000){const b=Math.floor(Date.now()/window),_id='mail:'+digest(key)+':'+b,c=db.collection('auth_limits');await c.updateOne({_id},{$inc:{count:1},$setOnInsert:{expiresAt:new Date((b+2)*window)}},{upsert:true});const row=await c.findOne({_id});if(row.count>max)fail(429,'Limite de e-mails ou tentativas atingido. Aguarde antes de tentar novamente.');}
const publicRecovery='Se houver um e-mail confirmado nessa conta, enviaremos um código. Confira também a pasta de spam.';
export function mailHandler({getDB=database,send=deliverMail,isConfigured=mailConfigured}={}){return async req=>{try{
 if(!configured())fail(503,'Configure o segredo de sessão.');const path=new URL(req.url).pathname;
 if(req.method!=='GET'&&!sameOrigin(req))fail(403,'Origem não permitida.');
 const publicRoute=path==='/api/mail/recovery/request'||path==='/api/mail/recovery/confirm';
 if(!publicRoute&&!accountPrincipal(req))fail(401,'Entre em uma conta permanente para configurar seu e-mail.');
 if(!['GET','POST'].includes(req.method))fail(405,'Método não permitido.');
 let b={};if(req.method==='POST'){let size=0,chunks=[];if(req.body)for await(const chunk of req.body){size+=chunk.byteLength;if(size>4096)fail(413,'Solicitação muito grande.');chunks.push(Buffer.from(chunk));}try{b=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{fail(400,'JSON inválido.');}}
 const db=await getDB(),users=db.collection('accounts'),challenges=db.collection('mail_challenges'),principal=accountPrincipal(req);let user=principal?await users.findOne({userId:principal.userId,sessionVersion:principal.version}):null;
 if(!publicRoute&&!user)fail(401,'Sessão encerrada. Entre novamente.');
 if(path==='/api/mail/status'&&req.method==='GET')return json({configured:isConfigured(),email:user.email??null,email_verified:!!user.emailVerified,personalized:!!user.personalizedMail,notice:'Confirme seu endereço para receber códigos de recuperação. Mensagens de plano são enviadas somente quando solicitadas.'});
 if(req.method!=='POST')fail(405,'Método não permitido.');
 if(path==='/api/mail/preferences'){fields(b,['personalized']);if(typeof b.personalized!=='boolean')fail(422,'Preferência inválida.');await users.updateOne({_id:user._id},{$set:{personalizedMail:b.personalized}});return json({status:'saved'});}
 if(!isConfigured())fail(503,'E-mail ainda não ativado pela equipe. Use o código de recuperação salvo.');
 if(path==='/api/mail/address/request'||path==='/api/mail/recovery/request'){
  let email,kind;if(publicRoute){fields(b,['username']);if(typeof b.username!=='string'||!/^[a-z0-9][a-z0-9_-]{2,31}$/i.test(b.username.trim()))fail(422,'Informe seu nome de usuário.');const name=b.username.trim().toLowerCase();await quota(db,'recover:'+name,3);await quota(db,'public-recovery',100,86400000);user=await users.findOne({_id:name});if(!user?.emailVerified||!user.email)return json({detail:publicRecovery});email=user.email;kind='recover';}
  else{fields(b,['email']);email=address(b.email);kind='verify';await quota(db,'verify-user:'+user.userId,3);await quota(db,'verify-target:'+email,3);}
  await quota(db,'all-mail',200,86400000);const code=String(randomInt(1000000)).padStart(6,'0'),nonce=randomBytes(16).toString('hex'),_id=kind+':'+user.userId,otpHash=digest(_id+':'+nonce+':'+code),expiresAt=new Date(Date.now()+600000);
  await challenges.updateOne({_id},{$set:{kind,userId:user.userId,username:user._id,email,nonce,otpHash,expiresAt,tries:0,version:user.sessionVersion}},{upsert:true});
  await send({to:email,subject:kind==='verify'?'Confirme seu e-mail no Aether AI':'Código de recuperação do Aether AI',text:'Olá, '+user._id+'.\n\nSeu código '+(kind==='verify'?'de confirmação':'de recuperação')+' é: '+code+'\n\nEle vence em 10 minutos e só pode ser usado uma vez. Se você não solicitou, ignore esta mensagem. A equipe nunca pede seu código por chat.'});
  return json({detail:kind==='recover'?publicRecovery:'Código enviado para '+mask(email)+'. Confira a caixa de entrada e o spam.'});
 }
 if(path==='/api/mail/address/confirm'||path==='/api/mail/recovery/confirm'){
  fields(b,publicRoute?['username','code','password']:['code']);if(typeof b.code!=='string'||!/^\d{6}$/.test(b.code))fail(422,'Informe o código de seis dígitos.');
  const kind=publicRoute?'recover':'verify';if(publicRoute){if(typeof b.username!=='string'||!/^[a-z0-9][a-z0-9_-]{2,31}$/i.test(b.username.trim()))fail(422,'Informe seu usuário.');await quota(db,'confirm-recovery:'+b.username.trim().toLowerCase(),10);user=await users.findOne({_id:b.username.trim().toLowerCase()});if(!user)fail(401,'Código inválido ou expirado.');}
  const _id=kind+':'+user.userId,challenge=await challenges.findOneAndUpdate({_id,tries:{$lt:5},expiresAt:{$gt:new Date()},version:user.sessionVersion},{$inc:{tries:1}},{returnDocument:'after'});
  if(!challenge||(publicRoute&&(!user.emailVerified||challenge.email!==user.email))||!eq(digest(_id+':'+challenge.nonce+':'+b.code),challenge.otpHash))fail(401,'Código inválido ou expirado.');
  const secret=publicRoute?await passwordHash(b.password):null;
  const consumed=await challenges.deleteOne({_id,nonce:challenge.nonce,otpHash:challenge.otpHash});if(consumed.deletedCount!==1)fail(401,'Código já utilizado.');
  if(publicRoute){const recoveryCode=randomBytes(24).toString('hex'),recoveryHash=(await import('node:crypto')).createHash('sha256').update(recoveryCode).digest('hex');const changed=await users.updateOne({_id:user._id,sessionVersion:challenge.version,email:challenge.email,emailVerified:true},{$set:{secret,recoveryHash},$inc:{sessionVersion:1}});if(changed.modifiedCount!==1)fail(409,'A conta mudou. Solicite outro código.');return json({detail:'Senha atualizada. Guarde o novo código de recuperação offline.',recoveryCode,username:user._id},200,accountCookie(user.userId,challenge.version+1));}
  const saved=await users.updateOne({_id:user._id,sessionVersion:challenge.version},{$set:{email:challenge.email,emailVerified:true,personalizedMail:user.personalizedMail??false}});if(saved.matchedCount!==1&&saved.modifiedCount!==1)fail(409,'A conta mudou. Solicite outra confirmação.');return json({status:'verified',detail:'E-mail confirmado. Agora você pode receber códigos de recuperação.'});
 }
 if(path==='/api/mail/plan'){
  fields(b,[],[]);if(!user.emailVerified||!user.email)fail(409,'Confirme seu e-mail antes de enviar o plano.');if(!user.personalizedMail)fail(409,'Autorize mensagens personalizadas nas preferências.');await quota(db,'plan:'+user.userId,3);await quota(db,'all-mail',200,86400000);
  const plan=await repository(getDB)('account:'+user.userId,s=>connectedPlan(s));if(!plan.profile)fail(409,'Cadastre seu plano na Home antes de enviá-lo.');
  await send({to:user.email,subject:'Seu plano de economia — Aether AI',text:'Olá, '+user._id+'!\n\n'+plan.answer+'\n\nConta informada: R$ '+plan.profile.monthly_bill.toFixed(2)+'\nMeta mensal: R$ '+plan.target_bill.toFixed(2)+'\nDiferença pretendida no ano: R$ '+plan.annual_target_saving.toFixed(2)+'\n\nEsta é uma projeção baseada no cadastro, não uma garantia de economia. Você pode desativar mensagens personalizadas na página da sua conta.'});return json({status:'sent',detail:'Plano aceito pelo Gmail para envio. Confira sua caixa de entrada e o spam.'});
 }
 fail(404,'Rota de e-mail inexistente.');
 }catch(e){return json(e instanceof ApiError?{detail:e.message}:databaseError(e),e instanceof ApiError?e.status:503);}};}
export default mailHandler();
