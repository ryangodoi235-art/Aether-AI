import {randomUUID} from 'node:crypto';
import {database} from '../mongo.mjs';
import {initialState,fail,hash} from './domain.mjs';
export function repository(getDatabase=database){return async function transact(owner,operation){
 const db=await getDatabase(),c=db.collection('workspaces');
 for(let attempt=0;attempt<6;attempt++){
  const now=new Date();let row=await c.findOne({_id:owner,expiresAt:{$gt:now}});
  if(!row){try{await c.updateOne({_id:owner,expiresAt:{$lte:now}},{$set:{payloadJson:JSON.stringify(initialState()),version:0,generation:randomUUID(),expiresAt:new Date(Date.now()+86400000)}});await c.insertOne({_id:owner,generation:randomUUID(),version:0,payloadJson:JSON.stringify(initialState()),expiresAt:new Date(Date.now()+86400000)});}catch(e){if(e.code!==11000)throw e;}row=await c.findOne({_id:owner,expiresAt:{$gt:now}});if(!row)continue;}
  const state=JSON.parse(row.payloadJson);const result=await operation(state);
  const payloadJson=JSON.stringify(state);if(Buffer.byteLength(payloadJson)>4000000)fail(413,'A sessão atingiu o limite. Exporte a planta e inicie outra sessão.');
  const saved=await c.updateOne({_id:owner,generation:row.generation,version:row.version,expiresAt:{$gt:now}},{$set:{payloadJson},$inc:{version:1}});
  if(saved.modifiedCount===1)return result;
 }fail(409,'Há alterações simultâneas. Atualize e tente novamente.');
};}
export function once(state,key,body,operation){const fingerprint=hash(body),old=state.receipts.find(r=>r.key===key);if(old){if(old.fingerprint!==fingerprint)fail(409,'Identificador já utilizado com outro conteúdo.');return old.result;}const result=operation();state.receipts.push({key,fingerprint,result});state.receipts=state.receipts.slice(-32);return result;}
export function databaseError(error){if(error.message==='database_unconfigured')return {code:'DB_CONFIG_MISSING',detail:'Configure MONGODB_URI e MONGODB_DB no Netlify.'};if(error.code===18||error.codeName==='AuthenticationFailed')return {code:'DB_AUTH_FAILED',detail:'MongoDB recusou o usuário ou a senha. Confira a URI nas variáveis do Netlify.'};return {code:'DB_UNAVAILABLE',detail:'MongoDB indisponível. Confira o acesso de rede do Atlas e as variáveis do Netlify.'};}
