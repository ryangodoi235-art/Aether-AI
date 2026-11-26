import {randomUUID,createHash} from 'node:crypto';
import house from '../../../../backend/config/house.json' with {type:'json'};
export class ApiError extends Error {constructor(status,message){super(message);this.status=status;}}
export const fail=(status,message)=>{throw new ApiError(status,message);};
export const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function fields(v,allowed,required=allowed){if(!object(v)||Object.keys(v).some(k=>!allowed.includes(k))||required.some(k=>!Object.hasOwn(v,k)))fail(422,'Campos inválidos ou ausentes.');return v;}
export function number(v,lo,hi,integer=false){if(typeof v!=='number'||!Number.isFinite(v)||v<lo||v>hi||(integer&&!Number.isInteger(v)))fail(422,'Valor fora dos limites.');return v;}
export function text(v,max=100){if(typeof v!=='string'||!v.trim()||v.trim().length>max)fail(422,'Texto inválido ou muito longo.');return v.trim();}
export function bool(v){if(typeof v!=='boolean')fail(422,'Informe um valor booleano.');return v;}
export function id(v){v=text(v);if(!/^[a-zA-Z0-9_-]{1,100}$/.test(v))fail(422,'ID inválido.');return v;}
export const norm=s=>String(s).toLowerCase().normalize('NFD').replace(/\p{M}/gu,'').replace(/[^a-z0-9]+/g,' ').trim();
export const rounded=(v,n=3)=>Math.round((v+Number.EPSILON)*10**n)/10**n;
export const hash=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
export const CATALOG={fridge:{name:'Geladeira',watts:150,hours:8},tv:{name:'Televisão',watts:120,hours:4},ac:{name:'Ar-condicionado',watts:1000,hours:6},shower:{name:'Chuveiro elétrico',watts:5500,hours:.4},stove:{name:'Fogão elétrico',watts:1800,hours:1},microwave:{name:'Micro-ondas',watts:1200,hours:.2},washer:{name:'Máquina de lavar',watts:500,hours:1},lights:{name:'Luz',watts:10,hours:5},fan:{name:'Ventilador',watts:65,hours:6}};
export function template(model){
 const split=model==='house'?5:4;
 const rooms=[{id:'sala',name:'Sala',x:0,z:0,w:split,d:4},{id:'quarto',name:'Quarto',x:split,z:0,w:4,d:4},{id:'cozinha',name:'Cozinha',x:0,z:4,w:split,d:3},{id:'banheiro',name:'Banheiro',x:split,z:4,w:4,d:3}];
 const devices=[['tv','sala'],['ac','quarto'],['fridge','cozinha'],['stove','cozinha'],['shower','banheiro'],['lights','sala']].map(([kind,room_id])=>({id:randomUUID(),kind,room_id,on:false,hours:CATALOG[kind].hours,...(kind==='lights'?{rgb_enabled:false,color:'#ffffff',brightness:100}:{})}));
 return {model,rooms,devices,tariff:1,goal:20,revision:0,sensor_presence:{}};
}
export function initialState(){return {active:'house',scenes:{house:template('house'),apartment:template('apartment')},catalog:structuredClone(house),catalogRevision:0,deviceStates:{},temperature:[],commands:[],automation:{enabled:false,sensor_id:'sensor-temperatura-sala',target_id:'tomada-sala',on_at:28,off_at:25},automationEvents:[],routines:[],runs:[],energySamples:[],profile:null,energyScene:{revision:0,devices:[]},history:[],pending:{},sensorSamples:{},receipts:[]};}
export const scene=s=>s.scenes[s.active];
export function watts(d){return d.on?CATALOG[d.kind].watts*(d.kind==='lights'?(d.brightness??100)/100:1):0;}
export function publicScene(s){const kwh=s.devices.reduce((a,d)=>a+watts(d)/1000*d.hours*30,0),base=s.devices.reduce((a,d)=>a+CATALOG[d.kind].watts/1000*d.hours*30,0);return {...s,catalog:CATALOG,source:'simulation',monthly_kwh:rounded(kwh),monthly_cost:rounded(kwh*s.tariff,2),baseline_cost:rounded(base*s.tariff,2),goal_cost:rounded(base*s.tariff*(1-s.goal/100),2)};}
export function exportDocument(s){const {model,rooms,devices,tariff,goal,sensor_presence={}}=s;return {schema_version:'aether-floorplan-1',project:structuredClone({model,rooms,devices,tariff,goal,sensor_presence})};}
export function validateDocument(doc){
 fields(doc,['schema_version','project']);if(doc.schema_version!=='aether-floorplan-1')fail(422,'Use o formato aether-floorplan-1.');
 const p=structuredClone(doc.project);fields(p,['model','rooms','devices','tariff','goal','sensor_presence'],['model','rooms','devices','tariff','goal']);
 if(!['house','apartment'].includes(p.model)||!Array.isArray(p.rooms)||!p.rooms.length||p.rooms.length>20||!Array.isArray(p.devices)||p.devices.length>100)fail(422,'Use casa/apartamento, 1–20 cômodos e até 100 aparelhos.');
 const ids=new Set(),names=new Set();
 for(const r of p.rooms){fields(r,['id','name','x','z','w','d']);id(r.id);r.name=text(r.name,50);if(ids.has(r.id)||names.has(r.name.toLowerCase()))fail(422,'Cômodos duplicados.');ids.add(r.id);names.add(r.name.toLowerCase());number(r.x,0,200);number(r.z,0,200);number(r.w,2,12);number(r.d,2,12);}
 for(let i=0;i<p.rooms.length;i++)for(const b of p.rooms.slice(i+1)){const a=p.rooms[i];if(a.x<b.x+b.w-.001&&a.x+a.w>b.x+.001&&a.z<b.z+b.d-.001&&a.z+a.d>b.z+.001)fail(422,'Os cômodos não podem se sobrepor.');}
 const seen=new Set(),counts={};for(const d of p.devices){fields(d,['id','kind','room_id','on','hours','rgb_enabled','color','brightness','u','v'],['id','kind','room_id','on','hours']);id(d.id);if(seen.has(d.id)||!Object.hasOwn(CATALOG,d.kind)||!ids.has(d.room_id))fail(422,'Aparelho ou cômodo inválido.');seen.add(d.id);if((counts[d.room_id]=(counts[d.room_id]||0)+1)>6)fail(422,'Limite de seis aparelhos por cômodo.');bool(d.on);number(d.hours,0,24);for(const k of ['u','v'])if(k in d)number(d[k],.15,.85);if(['rgb_enabled','color','brightness'].some(k=>k in d)&&d.kind!=='lights')fail(422,'RGB/brilho são exclusivos das luzes.');if('rgb_enabled'in d)bool(d.rgb_enabled);if('brightness'in d)number(d.brightness,0,100);if('color'in d&&(typeof d.color!=='string'||!/^#[a-f\d]{6}$/i.test(d.color)))fail(422,'Cor inválida.');}
 p.sensor_presence??={};if(!object(p.sensor_presence)||Object.entries(p.sensor_presence).some(([k,v])=>!ids.has(k)||typeof v!=='boolean'))fail(422,'Presença simulada inválida.');number(p.tariff,.01,10);number(p.goal,1,80);return p;
}
function addDevice(s,data){if(!Object.hasOwn(CATALOG,data.kind)||!s.rooms.some(r=>r.id===data.room_id))fail(422,'Aparelho ou cômodo inválido.');if(s.devices.length>=100||s.devices.filter(d=>d.room_id===data.room_id).length>=6)fail(422,'Limite de aparelhos atingido.');const d={id:randomUUID(),kind:data.kind,room_id:data.room_id,on:false,hours:CATALOG[data.kind].hours};if('rgb_enabled'in data){if(d.kind!=='lights')fail(422,'RGB exige uma luz.');bool(data.rgb_enabled);}if(d.kind==='lights')Object.assign(d,{rgb_enabled:data.rgb_enabled??false,color:'#ffffff',brightness:100});s.devices.push(d);return d;}
export function mutateScene(s,op,data){
 if(!object(data))fail(422,'Dados inválidos.');
 if(op==='add_device'){fields(data,['kind','room_id','rgb_enabled'],['kind','room_id']);addDevice(s,data);}
 else if(op==='device'||op==='remove_device'){
  fields(data,op==='remove_device'?['id']:['id','on','hours','rgb_enabled','color','brightness','u','v'],['id']);const d=s.devices.find(x=>x.id===data.id);if(!d)fail(404,'Aparelho não encontrado.');
  if(op==='remove_device')s.devices=s.devices.filter(x=>x.id!==d.id);
  else{if('on'in data)d.on=bool(data.on);if('hours'in data)d.hours=number(data.hours,0,24);if(['rgb_enabled','color','brightness'].some(k=>k in data)&&d.kind!=='lights')fail(422,'Cor e brilho exigem uma luz compatível.');if('rgb_enabled'in data)d.rgb_enabled=bool(data.rgb_enabled);if('brightness'in data)d.brightness=number(data.brightness,0,100);if('color'in data){if(!d.rgb_enabled||typeof data.color!=='string'||!/^#[a-f\d]{6}$/i.test(data.color))fail(422,'Esta luz não aceita essa cor RGB.');d.color=data.color.toLowerCase();}for(const k of ['u','v'])if(k in data)d[k]=number(data[k],.15,.85);}
 }else if(op==='room'||op==='add_room'){
  fields(data,['id','name','w','d','manual_position','x','z'],op==='room'?['id']:[]);
  let r=s.rooms.find(x=>x.id===data.id);
  if(op==='add_room'){if(s.rooms.length>=20)fail(422,'Limite de 20 cômodos.');r={id:randomUUID(),name:'Novo cômodo',x:0,z:0,w:3,d:3};s.rooms.push(r);}if(!r)fail(404,'Cômodo não encontrado.');
  let name=text(data.name??r.name,50);const others=s.rooms.filter(x=>x.id!==r.id).map(x=>norm(x.name));if(others.includes(norm(name))){if(op==='room')fail(422,'Já existe um cômodo com esse nome.');const base=name;let i=2;while(others.includes(norm(name)))name=base+' '+i++;}
  Object.assign(r,{name,w:number(data.w??r.w,2,12),d:number(data.d??r.d,2,12)});
  if(data.manual_position===true){r.x=number(data.x??r.x,0,200);r.z=number(data.z??r.z,0,200);}else{let z=0;for(let i=0;i<s.rooms.length;i+=2){const a=s.rooms[i],b=s.rooms[i+1];a.x=0;a.z=z;if(b){b.x=a.w;b.z=z;}z+=Math.max(a.d,b?.d??0);}}
 }else if(op==='remove_room'){
  fields(data,['id','confirm'],['id']);if(!s.rooms.some(r=>r.id===data.id))fail(404,'Cômodo não encontrado.');if(s.rooms.length===1)fail(422,'Mantenha ao menos um cômodo.');if(s.devices.some(d=>d.room_id===data.id)&&data.confirm!==true)fail(409,'Confirme a remoção dos aparelhos do cômodo.');s.rooms=s.rooms.filter(r=>r.id!==data.id);s.devices=s.devices.filter(d=>d.room_id!==data.id);delete s.sensor_presence[data.id];
 }else if(op==='sensor_presence'){fields(data,['room_id','present']);if(!s.rooms.some(r=>r.id===data.room_id))fail(422,'Cômodo inválido.');s.sensor_presence[data.room_id]=bool(data.present);}
 else if(op==='settings'){fields(data,['tariff','goal'],[]);s.tariff=number(data.tariff??s.tariff,.01,10);s.goal=number(data.goal??s.goal,1,80);}
 else if(op==='import_plan'){fields(data,['document','confirm']);if(data.confirm!==true)fail(409,'Confirme a substituição da planta.');const p=validateDocument(data.document);if(p.model!==s.model)fail(409,'Selecione o mesmo modelo do arquivo.');Object.assign(s,p);}
 else fail(422,'Operação desconhecida.');
 validateDocument(exportDocument(s));s.revision++;return publicScene(s);
}
export function sceneAction(state,b){fields(b,['request_id','project','revision','op','data'],['project','revision','op','data']);text(b.request_id??randomUUID());number(b.revision,0,Number.MAX_SAFE_INTEGER,true);let s=scene(state);if(s.model!==b.project||s.revision!==b.revision)fail(409,'A maquete mudou. Atualize antes de tentar novamente.');if(b.op==='model'){fields(b.data,['model']);if(!['house','apartment'].includes(b.data.model))fail(422,'Modelo inválido.');state.active=b.data.model;state.pending={};return publicScene(scene(state));}const result=mutateScene(s,b.op,b.data);if(['remove_room','remove_device','import_plan'].includes(b.op))state.pending={};return result;}
export function sensors(state,now=Date.now()){
 const s=scene(state),previous=state.sensorSamples[s.model],elapsed=previous?Math.max(0,Math.min(30,(now-previous.created)/1000)):0;
 const power=s.devices.reduce((a,d)=>a+watts(d),0),energy=(previous?.energy_kwh??0)+(previous?.power_w??0)*elapsed/3600000;
 const rooms=s.rooms.map((r,i)=>{const active=s.devices.filter(d=>d.room_id===r.id&&d.on).map(d=>d.kind);return {room_id:r.id,sensor_id:'sim-'+r.id,temperature_c:rounded(25+i*.25+Math.sin(now/90000+i)*.4-(active.includes('ac')?2:0)+(active.includes('shower')?1:0),1),humidity_percent:rounded(52+Math.sin(now/100000+i)*2+(active.includes('shower')?12:0)-(active.includes('ac')?5:0),1),presence:s.sensor_presence[r.id]??true,power_w:rounded(s.devices.filter(d=>d.room_id===r.id).reduce((a,d)=>a+watts(d),0),2)};});
 const result={source:'simulation',physical:false,timestamp:new Date(now).toISOString(),model:s.model,revision:s.revision,voltage_v:220,power_w:rounded(power,2),current_a:rounded(power/220),energy_kwh:energy,integration_seconds:elapsed,rooms,notice:'Sensores fictícios sob demanda. 220 V e fator de potência 1 são hipóteses. Integração limitada a 30 s entre amostras.'};
 if(!previous||now-previous.created>=4000)state.sensorSamples[s.model]={created:now,energy_kwh:energy,power_w:power};return result;
}
