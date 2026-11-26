import {createHmac,randomBytes,timingSafeEqual,createHash} from 'node:crypto';
const cookieName='__Host-aether_test';
const equal=(a,b)=>timingSafeEqual(createHash('sha256').update(a).digest(),createHash('sha256').update(b).digest());
export function configured(){return (process.env.AETHER_TEST_PASSWORD||'').length>=12&&(process.env.AETHER_SESSION_SECRET||'').length>=32;}
function signature(value){return createHmac('sha256',process.env.AETHER_SESSION_SECRET).update(value).digest('base64url');}
export function authenticated(req){
 if(!configured())return false;
 const value=(req.headers.get('cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='))?.slice(cookieName.length+1);
 if(!value||value.length>300)return false;
 const [expires,nonce,sig,...extra]=value.split('.');
 return !extra.length&&/^\d+$/.test(expires)&&Number(expires)>Date.now()&&Number(expires)<=Date.now()+43201000&&!!nonce&&!!sig&&equal(sig,signature(expires+'.'+nonce));
}
export function sameOrigin(req){return req.headers.get('origin')===new URL(req.url).origin;}
// A session-scoped pseudonymous owner; never trust a client-supplied owner ID.
export function sessionOwner(req){
 if(!authenticated(req))return null;
 const value=(req.headers.get('cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='))?.slice(cookieName.length+1);
 return createHmac('sha256',process.env.AETHER_SESSION_SECRET).update('mongo-owner:'+value).digest('hex');
}
export async function access(req){
 const response=(status,detail,headers={})=>Response.json({detail},{status,headers:{'Cache-Control':'no-store',...headers}});
 if(!configured())return response(503,'Configure uma senha de testes com 12 caracteres ou mais e um segredo de sessão com 32 caracteres ou mais.');
 if(req.method==='GET')return response(authenticated(req)?200:401,authenticated(req)?'Conectado.':'Entre para testar.');
 if(!['POST','DELETE'].includes(req.method))return response(405,'Método não permitido.');
 if(!sameOrigin(req))return response(403,'Origem não permitida.');
 if(req.method==='DELETE')return response(200,'Sessão encerrada.',{'Set-Cookie':cookieName+'=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict'});
 const raw=await req.text();if(raw.length>2048)return response(413,'Solicitação excessiva.');
 let body;try{body=JSON.parse(raw);}catch{return response(400,'Formato inválido.');}
 if(typeof body.password!=='string'||!equal(body.password,process.env.AETHER_TEST_PASSWORD))return response(401,'Senha incorreta.');
 const value=String(Date.now()+43200000)+'.'+randomBytes(16).toString('hex');
 return response(200,'Acesso liberado.',{'Set-Cookie':cookieName+'='+value+'.'+signature(value)+'; Path=/; Max-Age=43200; HttpOnly; Secure; SameSite=Strict'});
}

