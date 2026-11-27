import {interpret} from './language.mjs';
import {classify,predictEnergy,metrics} from './neural.mjs';
import {sessionOwner} from '../access.mjs';
import {repository,once,databaseError} from './store.mjs';
import {ApiError,fail,fields,text,number,scene,publicScene,sceneAction,sensors,exportDocument,validateDocument,CATALOG,norm,mutateScene} from './domain.mjs';
import {profile,plan,energyScene,syncProfile,connectedPlan} from './energy.mjs';
const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
async function body(req){let size=0,chunks=[];if(req.body)for await(const chunk of req.body){size+=chunk.byteLength;if(size>1000000)fail(413,'Limite de 1 MB por solicitação.');chunks.push(Buffer.from(chunk));}try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{fail(400,'JSON inválido.');}}
export function nativeHandler(transact=repository()){return async function(req){try{
 const url=new URL(req.url),path=url.pathname.replace('/api/v1',''),method=req.method,b=['POST','PUT'].includes(method)?await body(req):null;
 if(path==='/deployment/status')return json({mode:'netlify-mongodb',simulation:true,session_scope:'browser_login',voice:'browser-dependent',ollama:false,pdf_import:false});
 if(path==='/voice/status')return json({recognition_ready:false,speech_ready:false,message:'A voz online usa recursos do navegador, com compatibilidade e privacidade indicadas no painel de voz. Whisper/Piper continuam na instalação Python.'});
 if(path==='/hardware/status')return json({status:'unavailable',message:'Demonstração online: sensores e aparelhos fictícios.'});
 if(path.startsWith('/voice/')||path.startsWith('/hardware/'))fail(501,'Recurso disponível na instalação local do Aether.');
 if(path==='/neural/classify'&&method==='POST')return json(classify(text(b.text,800)));
 if(['/neural/predict','/neural/forecast'].includes(path)&&method==='POST')return json(predictEnergy(b.features));
 if(path==='/neural/status'&&method==='GET')return json({ready:true,models:['aether-intent-mlp-v20','aether-energy-mlp-v20'],execution:'netlify-functions',metrics,notice:'Avaliação sintética, sem comprovação de economia ou entendimento geral.'});
 if(path==='/assistant/status')return json({status:'ready',model:'aether-mlp-v20' ,message:'Comandos da maquete disponíveis. Conversa livre via Ollama permanece na instalação local.'});
 if(path==='/forecasts/status')return json({status:'unavailable',message:'Modelo histórico disponível na instalação local.'});
 if(['/forecasts','/forecasts/demo-inputs'].includes(path)&&method==='GET')return json([]);
 const result=await transact(sessionOwner(req),state=>{
  const s=scene(state);
  if(path==='/database/status'&&method==='GET')return {status:'ready',mode:'netlify-mongodb'};
  if(path==='/maquette'&&method==='GET')return publicScene(s);
  if(path==='/maquette/sensors'&&method==='GET')return sensors(state);
  if(path==='/maquette/export'&&method==='GET')return exportDocument(s);
  if(path==='/maquette/import-preview'&&method==='POST'){const p=validateDocument(b);return {model:p.model,rooms:p.rooms.length,devices:p.devices.length,document:exportDocument(p)};}
  if(path==='/maquette/action'&&method==='POST')return once(state,path+':'+text(b.request_id??'revision-'+b.project+'-'+b.revision),b,()=>sceneAction(state,b));
  if(path==='/energy-coach/profile'){
   if(method==='GET')return connectedPlan(state);
   if(method==='PUT'){return syncProfile(state,profile(b));}
   if(method==='DELETE'){state.profile=null;return {status:'removed'};}
  }
  if(path==='/energy-coach/scene'){
   if(method==='GET')return energyScene(state);
   if(method==='PUT'){fields(b,['revision','devices']);if(b.revision!==state.energyScene.revision)fail(409,'Cenário mudou. Atualize.');if(!Array.isArray(b.devices)||b.devices.length>36)fail(422,'Aparelhos inválidos.');const seen=new Set();for(const d of b.devices){fields(d,['kind','room','on','hours']);if(!Object.hasOwn(CATALOG,d.kind)||typeof d.on!=='boolean')fail(422,'Aparelho inválido.');number(d.room,0,3,true);number(d.hours,0,24);const key=d.kind+':'+d.room;if(seen.has(key))fail(422,'Aparelho duplicado.');seen.add(key);}state.energyScene={revision:b.revision+1,devices:b.devices};return energyScene(state);}
  }
  if(path==='/house'&&method==='GET')return {...state.catalog,source:'simulation'};
  if(path==='/devices'&&method==='GET')return state.catalog.devices.map(d=>({...d,source:'simulation',state:state.deviceStates[d.id]?.state??d.initial_state??'unknown',...state.deviceStates[d.id]}));

  if(path.match(/^\/sensors\/[^/]+\/readings$/)&&method==='GET')return {readings:[],total:0,source:'simulation'};
  if(path==='/commands'&&method==='POST')return once(state,path+':'+text(b.request_id),b,()=>{
   fields(b,['request_id','device_id','action','brightness','color'],['request_id','device_id','action']);const d=state.catalog.devices.find(d=>d.id===b.device_id);if(!d)fail(404,'Dispositivo não encontrado.');if(!d.available)fail(503,'Dispositivo indisponível.');if(!d.capabilities.includes(b.action))fail(422,'Ação incompatível.');const value=state.deviceStates[d.id]??{state:d.initial_state};
   if(b.action==='turn_on'||b.action==='turn_off'){if('brightness'in b||'color'in b)fail(422,'Parâmetros incompatíveis.');value.state=b.action==='turn_on'?'on':'off';}
   else if(b.action==='set_brightness'){if('color'in b)fail(422,'Parâmetros incompatíveis.');value.brightness=number(b.brightness,0,100,true);value.state=b.brightness?'on':'off';}
   else if(b.action==='set_color'){if(value.state!=='on')fail(409,'Ligue a luz antes de aplicar a cor.');if('brightness'in b||!Array.isArray(b.color)||b.color.length!==3)fail(422,'Cor inválida.');b.color.forEach(v=>number(v,0,255,true));value.color=b.color;}
   else fail(422,'Ação desconhecida.');state.deviceStates[d.id]=value;return {request_id:b.request_id,device_id:d.id,action:b.action,status:'confirmed',source:'simulation',...value,timestamp:new Date().toISOString()};
  });
  if(path==='/catalog'&&method==='GET')return {revision:String(state.catalogRevision),house:state.catalog};
  if(path==='/automation'&&method==='GET')return state.automation;
  if(['/automation/events','/events','/routines','/routines/runs/history'].includes(path)&&method==='GET')return [];
  if(path==='/assistant/history'&&method==='GET'){const limit=Math.min(100,Math.max(1,Number(url.searchParams.get('limit'))||20));return state.history.filter(x=>!url.searchParams.has('session_id')||x.session_id===url.searchParams.get('session_id')).slice(-limit).reverse();}
  if(path==='/assistant/feedback'&&method==='POST'){
   fields(b,['message_id','rating'],['message_id','rating']);if(!['helpful','incorrect','unclear'].includes(b.rating))fail(422,'Avaliação inválida.');const message=state.history.find(m=>m.id===b.message_id);if(!message)fail(404,'Mensagem não encontrada nesta conta.');state.feedback??=[];state.feedback=state.feedback.filter(f=>f.message_id!==b.message_id);state.feedback.push({message_id:b.message_id,rating:b.rating,question:message.question,predicted_intent:message.neural?.intent??null,timestamp:new Date().toISOString()});state.feedback=state.feedback.slice(-200);return {status:'saved',notice:'Avaliação salva apenas no seu espaço. Não altera automaticamente os pesos da rede neural.'};
  }
  if(path==='/assistant/feedback'&&method==='GET')return {samples:state.feedback??[],notice:'Avaliações do próprio usuário. Requer revisão humana antes de usar em treino.'};
  if(path==='/assistant/chat'&&method==='POST'){
   fields(b,['text','request_id','session_id','target'],['text']);const q=text(b.text,800),sid=text(b.session_id??'default'),rid=text(b.request_id??crypto.randomUUID());return once(state,path+':'+rid,b,()=>{
    const language=interpret(q,s),decision=classify(q),phrase=language.phrase;let answer='Posso ajudar com a maquete: peça para adicionar um aparelho, ligar ou desligar, informando o cômodo. A conversa livre com Ollama funciona na instalação local.',changed=false,status='answered';
    const {rooms,kinds}=language,key=sid+':'+(b.target??'auto'),pending=state.pending[key];
    if(phrase!=='confirmar acao')delete state.pending[key];
    if(['cancelar','cancele'].includes(phrase)){delete state.pending[key];answer='Pedido cancelado.';}
    else if(phrase==='confirmar acao'&&pending){if(Date.now()-pending.created>300000||pending.model!==s.model||pending.revision!==s.revision){delete state.pending[key];answer='A maquete mudou ou o pedido expirou. Faça o pedido novamente.';}else{mutateScene(s,pending.op,pending.data);delete state.pending[key];changed=true;status='confirmed';answer='Pronto. Atualizei a maquete na simulação.';}}
    else if(b.target==='devices')answer='Use os controles dos dispositivos cadastrados nesta demonstração. O chat online atende à maquete.';
    else if(language.denied&&language.action)answer='Nenhuma alteração feita. Para uma ação, informe diretamente o aparelho e o cômodo.';
    else if(/^(adicione|crie|adicionar) (?:um |uma )?(?:comodo|ambiente|quarto|sala)/.test(phrase)&&!kinds.length){const match=q.match(/(?:chamad[oa]|com (?:o )?nome)\s+(.+)$/i);if(!match)answer='Diga, por exemplo: crie um cômodo chamado Escritório.';else{state.pending[key]={op:'add_room',data:{name:text(match[1],50)},model:s.model,revision:s.revision,created:Date.now()};answer='Vou adicionar o cômodo na simulação. Digite “confirmar ação”.';status='needs_confirmation';}}
    else if(language.action==='remove'&&!kinds.length&&rooms.length===1&&!language.compound){state.pending[key]={op:'remove_room',data:{id:rooms[0].id,confirm:true},model:s.model,revision:s.revision,created:Date.now()};answer='Vou remover '+rooms[0].name+' e seus aparelhos da simulação. Digite “confirmar ação”.';status='needs_confirmation';}
    else if(kinds.length===1&&rooms.length){const room=rooms[0],kind=kinds[0];let op,data;if(language.action==='add'){op='add_device';data={kind,room_id:room.id};}else if(['on','off','remove'].includes(language.action)){const ds=s.devices.filter(d=>d.room_id===room.id&&d.kind===kind);if(ds.length===1){op=language.action==='remove'?'remove_device':'device';data=language.action==='remove'?{id:ds[0].id}:{id:ds[0].id,on:language.action==='on'};}else answer='Encontrei nenhum ou mais de um aparelho desse tipo no cômodo. Use os controles da maquete.';}if(op){if(rooms.length>1||language.compound)answer='Faça um pedido por vez para evitar alterar o aparelho errado.';else{state.pending[key]={op,data,model:s.model,revision:s.revision,created:Date.now()};answer=`Vou ${op==='add_device'?'adicionar':op==='remove_device'?'remover':'alterar'} ${CATALOG[kind].name} em ${room.name}, na simulação. Digite “confirmar ação”.`;status='needs_confirmation';}}}
    else if(kinds.length===1&&language.action&&!rooms.length)answer='Informe o nome do cômodo cadastrado, por exemplo: adicione uma geladeira na cozinha.';
    else if(/\b(economia|economizar|meta|conta)\b/.test(phrase))answer=state.profile?connectedPlan(state).answer:'Preencha seu plano de economia na Home para calcular uma meta baseada na conta informada.';
    if(/^(oi|ola|bom dia|boa tarde|boa noite)$/.test(phrase))answer='Olá! Posso ajudar a montar sua maquete e planejar a economia. O que deseja fazer?';
    if(/quais.*comodos|liste.*comodos/.test(phrase)&&!language.action)answer='Seus cômodos são: '+s.rooms.map(r=>r.name).join(', ')+'.';
    const response={id:crypto.randomUUID(),request_id:rid,session_id:sid,status,answer,actions_executed:changed,model:'aether-mlp-v20' ,response_source:'netlify_neural_and_rules',neural:decision,prompt_version:'netlify-v1',timestamp:new Date().toISOString(),context:{source:'simulation',target:'maquette',maquette:publicScene(s)},notice:'Demonstração simulada. MLP experimental e validação por regras; Ollama não é executado no Netlify.'};state.history.push({...response,question:q});state.history=state.history.slice(-60);return response;
   });
  }
  if(path.startsWith('/maquette/files/')||path.startsWith('/maquette/openplan/'))fail(501,'Conversão de PDF e editor OpenPlan disponíveis na instalação local. Importe ou exporte JSON nesta demonstração.');
  fail(404,'Recurso não disponível nesta demonstração online.');
 });return json(result);
 }catch(e){if(e instanceof ApiError)return json({detail:e.message},e.status);return json(databaseError(e),503);}};}
export default nativeHandler();
