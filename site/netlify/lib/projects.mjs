import {randomUUID} from 'node:crypto';
import {sessionOwner,sameOrigin} from './access.mjs';
import {database} from './mongo.mjs';
const json=(status,value)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const root='/api/v1/cloud/projects';
const uuid=/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/;
async function readBody(request){
 const chunks=[];let size=0;
 if(!request.body)throw {status:400};
 const reader=request.body.getReader();
 try{
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>1000000)throw {status:413};chunks.push(value);}
 }finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;
 for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
 try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw {status:400};}
}
export function validateProject(body){
 if(!body||typeof body!=='object'||Array.isArray(body)||Object.keys(body).some(k=>!['title','document'].includes(k)))throw {status:422};
 if(typeof body.title!=='string'||body.title.trim().length<1||body.title.trim().length>100)throw {status:422};
 const d=body.document;
 if(!d||typeof d!=='object'||Array.isArray(d))throw {status:422};
 // Store a JSON file as text: its keys can never become Mongo query operators.
 const serialized=JSON.stringify(d);
 if(Buffer.byteLength(serialized)>950000)throw {status:413};
 return {title:body.title.trim(),documentJson:serialized};
}
// Injectable storage enables meaningful ownership/error tests without a live database.
export async function projects(request,getDatabase=database){
 const owner=sessionOwner(request);if(!owner)return json(401,{detail:'Entre para salvar seus projetos.'});
 if(request.method!=='GET'&&!sameOrigin(request))return json(403,{detail:'Origem não permitida.'});
 const path=new URL(request.url).pathname;
 const id=path===root?null:path.slice(root.length+1);
 if(path!==root&&(!path.startsWith(root+'/')||!uuid.test(id)))return json(404,{detail:'Projeto não encontrado.'});
 if(!(id?['GET','DELETE']:['GET','POST']).includes(request.method))return json(405,{detail:'Método não permitido.'});
 try{
  const payload=request.method==='POST'?validateProject(await readBody(request)):null;
  const db=await getDatabase();const collection=db.collection('demo_projects');
  const filter={owner,expiresAt:{$gt:new Date()}};
  if(id){
   const query={...filter,_id:id};
   if(request.method==='DELETE'){
    const result=await collection.deleteOne(query);
    return json(result.deletedCount?200:404,result.deletedCount?{status:'removed'}:{detail:'Projeto não encontrado.'});
   }
   const row=await collection.findOne(query);
   return row?json(200,{id:row._id,title:row.title,document:JSON.parse(row.documentJson),createdAt:row.createdAt,expiresAt:row.expiresAt}):json(404,{detail:'Projeto não encontrado.'});
  }
  if(request.method==='GET'){
   const rows=await collection.find(filter,{projection:{_id:1,title:1,createdAt:1,expiresAt:1}}).sort({createdAt:-1}).limit(50).toArray();
   return json(200,{projects:rows.map(({_id,...row})=>({id:_id,...row})),scope:'session',notice:'Cópias temporárias por sessão; baixe os arquivos antes de sair ou trocar de dispositivo.'});
  }
  const now=new Date();const row={_id:randomUUID(),owner,...payload,createdAt:now,expiresAt:new Date(now.getTime()+86400000)};
  await collection.insertOne(row);
  return json(201,{id:row._id,title:row.title,createdAt:row.createdAt,expiresAt:row.expiresAt});
 }catch(err){
  const status=[400,413,422].includes(err?.status)?err.status:503;
  return json(status,{detail:status===503?'MongoDB indisponível. Confira as variáveis e o acesso de rede.':status===413?'Arquivo deve ter até 950 KB.':'Informe um título e um documento JSON válido.'});
 }
}
