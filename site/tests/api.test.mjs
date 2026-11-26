import test from 'node:test';
import assert from 'node:assert/strict';
import handler from '../netlify/functions/api.mjs';
import {access,authenticated} from '../netlify/lib/access.mjs';
const origin='https://aether.example';
const req=(path='/api/v1/devices',options={})=>new Request(origin+path,options);
test('session, CSRF, gateway and binary responses',async()=>{
 process.env.AETHER_TEST_PASSWORD='test-only-password';process.env.AETHER_SESSION_SECRET='s'.repeat(48);
 assert.equal((await handler(req())).status,401);
 const login=await access(req('/api/session',{method:'POST',headers:{origin,'Content-Type':'application/json'},body:JSON.stringify({password:'test-only-password'})}));
 assert.equal(login.status,200);const cookie=login.headers.get('set-cookie').split(';')[0];
 assert.ok(login.headers.get('set-cookie').includes('HttpOnly'));assert.ok(login.headers.get('set-cookie').includes('Secure'));
 assert.ok(authenticated(req('/',{headers:{cookie}})));
 assert.ok(!authenticated(req('/',{headers:{cookie:cookie+'tamper'}})));
 assert.equal((await access(req('/api/session',{method:'POST',headers:{origin:'https://evil.example'},body:'{}'}))).status,403);
 assert.equal((await access(req('/api/session',{method:'POST',headers:{origin},body:JSON.stringify({password:'wrong'})}))).status,401);
 assert.equal((await handler(req('/api/v1/commands',{method:'POST',headers:{cookie,origin:'https://evil.example'},body:'{}'}))).status,403);
 delete process.env.AETHER_API_URL;delete process.env.AETHER_API_TOKEN;
 const authed=(path='/api/v1/devices',options={})=>req(path,{...options,headers:{cookie,origin,...options.headers}});
 assert.equal((await handler(authed())).status,503);
 process.env.AETHER_API_URL='http://unsafe.example';process.env.AETHER_API_TOKEN='backend-secret';
 assert.equal((await handler(authed())).status,503);process.env.AETHER_API_URL='https://backend.example';
 const original=globalThis.fetch;
 try{
 globalThis.fetch=async(url,options)=>{assert.equal(url.origin,'https://backend.example');assert.equal(options.headers['X-Aether-Token'],'backend-secret');assert.equal(options.headers.Cookie,undefined);return new Response(new Uint8Array([82,73,70,70]),{headers:{'Content-Type':'audio/wav'}});};
 const r=await handler(authed());assert.equal(r.status,200);assert.equal(r.headers.get('content-type'),'audio/wav');assert.equal(r.headers.get('x-aether-token'),null);assert.deepEqual([...new Uint8Array(await r.arrayBuffer())],[82,73,70,70]);
 assert.equal((await handler(authed('/api/v1/voice/transcribe',{method:'POST',body:'x'.repeat(3000001)}))).status,413);
 globalThis.fetch=async()=>new Response('{}',{status:422});assert.equal((await handler(authed())).status,422);
 globalThis.fetch=async()=>{throw Error('private');};const bad=await handler(authed());assert.equal(bad.status,502);assert.ok(!(await bad.text()).includes('private'));
 }finally{globalThis.fetch=original;}
});

