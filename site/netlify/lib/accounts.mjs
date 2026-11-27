import {randomBytes,scrypt as rawScrypt,timingSafeEqual,createHash} from 'node:crypto';
import {promisify} from 'node:util';
import {database} from './mongo.mjs';
import {authenticated,sameOrigin,configured,accountPrincipal,accountCookie} from './access.mjs';
import {ApiError,fail,fields} from './native/domain.mjs';
import {databaseError} from './native/store.mjs';
const scrypt=promisify(rawScrypt),digest=v=>createHash('sha256').update(v).digest('hex');
const eq=(a,b)=>timingSafeEqual(Buffer.from(digest(a),'hex'),Buffer.from(digest(b),'hex'));
const reply=(data,status=200,cookie)=>Response.json(data,{status,headers:{'Cache-Control':'no-store',...(cookie?{'Set-Cookie':cookie}:{})}});
let hashing=0;
export async function passwordHash(password,salt=randomBytes(16).toString('hex')){if(typeof password!=='string'||password.length<12||Buffer.byteLength(password)>256)fail(422,'Use uma senha de 12 caracteres ou mais, até 256 bytes.');if(hashing>=2)fail(429,'Autenticação ocupada. Tente novamente em instantes.');hashing++;try{const key=await scrypt(password,salt,64,{N:131072,r:8,p:1,maxmem:192*1024*1024});return {salt,hash:key.toString('hex'),algorithm:'scrypt-N131072-r8-p1'};}finally{hashing--;}}
function name(value){if(typeof value!=='string'||!/^[a-z0-9][a-z0-9_-]{2,31}$/i.test(value.trim()))fail(422,'Use um usuário de 3–32 letras, números, hífen ou sublinhado.');return value.trim().toLowerCase();}
async function limited(db,key,max){const bucket=Math.floor(Date.now()/900000),_id=key+':'+bucket,c=db.collection('auth_limits');await c.updateOne({_id},{$inc:{count:1},$setOnInsert:{expiresAt:new Date((bucket+2)*900000)}},{upsert:true});const r=await c.findOne({_id});if(r.count>max)fail(429,'Muitas tentativas. Aguarde até 15 minutos.');}
export async function validAccount(req,getDB=database){const p=accountPrincipal(req);if(!p)return true;const db=await getDB(),u=await db.collection('accounts').findOne({userId:p.userId,sessionVersion:p.version});return !!u;}
export function accountHandler(getDB=database){return async req=>{try{
 if(!configured())fail(503,'Configure a senha de convite e o segredo de sessão no servidor.');
 const path=new URL(req.url).pathname;
 if(path==='/api/account/me'&&req.method==='GET'){const p=accountPrincipal(req);if(!authenticated(req))fail(401,'Entre para continuar.');if(!p)return reply({mode:'demo',persistent:false});const db=await getDB(),u=await db.collection('accounts').findOne({userId:p.userId,sessionVersion:p.version});if(!u)fail(401,'Sessão encerrada. Entre novamente.');return reply({mode:'account',persistent:true,username:u._id});}
 if(req.method!=='POST')fail(405,'Método não permitido.');if(!sameOrigin(req))fail(403,'Origem não permitida.');
 const chunks=[];let size=0;if(req.body)for await(const chunk of req.body){size+=chunk.byteLength;if(size>4096)fail(413,'Solicitação muito grande.');chunks.push(Buffer.from(chunk));}
 let b;try{b=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{fail(400,'JSON inválido.');}
 if(!['/api/account/register','/api/account/login','/api/account/recover'].includes(path))fail(404,'Rota inexistente.');
 fields(b,path.endsWith('/register')?['username','password','invite']:path.endsWith('/recover')?['username','password','recoveryCode']:['username','password']);
 const username=name(b.username),db=await getDB(),users=db.collection('accounts');
 await limited(db,'global',200);await limited(db,'name:'+digest(username),10);
 if(path.endsWith('/register')){
  if(typeof b.invite!=='string'||!eq(b.invite,process.env.AETHER_TEST_PASSWORD))fail(403,'Convite inválido. Use a senha de convite fornecida pela equipe.');
  const secret=await passwordHash(b.password),recoveryCode=randomBytes(24).toString('hex'),userId=randomBytes(16).toString('hex');
  try{await users.insertOne({_id:username,userId,secret,recoveryHash:digest(recoveryCode),sessionVersion:0,createdAt:new Date()});}catch(e){if(e.code===11000)fail(409,'Este nome de usuário já está em uso.');throw e;}
  return reply({username,recoveryCode,detail:'Conta criada. Guarde o código de recuperação; ele aparece uma única vez.'},201,accountCookie(userId,0));
 }
 const user=await users.findOne({_id:username});
 if(path.endsWith('/recover')){
  if(typeof b.recoveryCode!=='string'||b.recoveryCode.length>100||!user||!eq(digest(b.recoveryCode.trim()),user.recoveryHash))fail(401,'Usuário ou código de recuperação inválido.');
  const secret=await passwordHash(b.password),recoveryCode=randomBytes(24).toString('hex');
  const result=await users.updateOne({_id:username,recoveryHash:user.recoveryHash},{$set:{secret,recoveryHash:digest(recoveryCode)},$inc:{sessionVersion:1}});if(result.modifiedCount!==1)fail(409,'O código já foi utilizado.');
  return reply({detail:'Senha atualizada. Sessões anteriores encerradas. Guarde o novo código.',recoveryCode,username},200,accountCookie(user.userId,user.sessionVersion+1));
 }
 // Perform the same expensive derivation for unknown users to reduce enumeration by timing.
 const candidate=await passwordHash(b.password,user?.secret.salt??'00000000000000000000000000000000');
 if(!user||!eq(candidate.hash,user.secret.hash))fail(401,'Usuário ou senha inválidos.');
 return reply({username,detail:'Conectado à sua conta.'},200,accountCookie(user.userId,user.sessionVersion));
 }catch(e){return reply(e instanceof ApiError?{detail:e.message}:databaseError(e),e instanceof ApiError?e.status:503);}};}
export default accountHandler();
