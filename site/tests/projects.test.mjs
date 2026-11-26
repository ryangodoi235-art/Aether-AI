import test from 'node:test';
import assert from 'node:assert/strict';
import {access} from '../netlify/lib/access.mjs';
import {projects} from '../netlify/lib/projects.mjs';
const origin='https://aether.example';
function req(path='/api/v1/cloud/projects',method='GET',cookie='',body){return new Request(origin+path,{method,headers:{origin,cookie,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});}
test('Mongo copies enforce ownership, validation, expiration and deletion',async()=>{
 process.env.AETHER_TEST_PASSWORD='test-only-password';process.env.AETHER_SESSION_SECRET='s'.repeat(48);
 async function login(){const r=await access(req('/api/session','POST','',{password:'test-only-password'}));return r.headers.get('set-cookie').split(';')[0];}
 const a=await login(),b=await login();const rows=[];
 const matches=(r,q)=>r.owner===q.owner&&r.expiresAt>q.expiresAt.$gt&&(!q._id||r._id===q._id);
 const collection={insertOne:async row=>{rows.push(row);},findOne:async q=>rows.find(r=>matches(r,q)),deleteOne:async q=>{const i=rows.findIndex(r=>matches(r,q));if(i<0)return {deletedCount:0};rows.splice(i,1);return {deletedCount:1};},find:q=>({sort:()=>({limit:()=>({toArray:async()=>rows.filter(r=>matches(r,q)).map(({documentJson,owner,...r})=>r)})})})};
 const db=async()=>({collection:()=>collection});
 assert.equal((await projects(req(),db)).status,401);
 assert.equal((await projects(req(undefined,'POST',a,{title:'A',document:{rooms:[]},owner:'forged'}),db)).status,422);
 const saved=await projects(req(undefined,'POST',a,{title:'Casa',document:{'$query':'plain data',rooms:[]}}),db);
 assert.equal(saved.status,201);const {id}=await saved.json();
 const path='/api/v1/cloud/projects/'+id;
 assert.equal((await projects(req(path,'GET',b),db)).status,404);
 assert.equal((await projects(req(path,'DELETE',b),db)).status,404);
 const list=await (await projects(req(undefined,'GET',b),db)).json();assert.equal(list.projects.length,0);
 const owned=await (await projects(req(path,'GET',a),db)).json();assert.equal(owned.document.$query,'plain data');assert.equal(owned.owner,undefined);
 const csrf=new Request(origin+path,{method:'DELETE',headers:{cookie:a,origin:'https://evil.example'}});assert.equal((await projects(csrf,db)).status,403);
 const huge={title:'Huge',document:{data:'a'.repeat(1000000)}};assert.equal((await projects(req(undefined,'POST',a,huge),db)).status,413);
 rows[0].expiresAt=new Date(0);assert.equal((await projects(req(path,'GET',a),db)).status,404);rows[0].expiresAt=new Date(Date.now()+10000);
 assert.equal((await projects(req(path,'DELETE',a),db)).status,200);assert.equal(rows.length,0);
 const unavailable=await projects(req(undefined,'GET',a),async()=>{throw Error('mongodb+srv://private:password@host');});assert.equal(unavailable.status,503);assert.ok(!(await unavailable.text()).includes('password'));
});
