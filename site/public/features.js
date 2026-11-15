/* Local feature controls; all displayed names use textContent. */
(()=>{
 const node=(t,text)=>{const e=document.createElement(t);if(text!==undefined)e.textContent=text;return e;};
 const notify=(text,error=false)=>status(text,error);
 async function call(path,body,method){const r=await fetch(path,{method:method||(body?'POST':'GET'),headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,cache:'no-store'});let data;try{data=await r.json();}catch{throw Error('Resposta inválida.');}if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;}
 function field(form,label,type='text',value=''){const l=node('label',label),e=node('input');e.type=type;e.value=value;l.append(e);form.append(l);return e;}
 function select(form,label,values){const l=node('label',label),s=node('select');s.setAttribute('aria-label',label);for(const [value,text] of values){const o=node('option',text);o.value=value;s.append(o);}l.append(s);form.append(l);return s;}
 function btn(parent,label,fn){const b=node('button',label);b.type='button';b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){notify(e.message,true);}finally{b.disabled=false;}};parent.append(b);return b;}
 function panel(id,title,description){const p=node('section');p.id=id;p.className='card feature-card';p.append(node('h2',title),node('p',description));document.getElementById('features-panel').append(p);return p;}
 async function catalogUI(){
  const p=panel('catalog-panel','Cômodos e dispositivos','Cadastre e edite sua casa. IDs preservam o histórico; desative itens que não usa mais.');
  const form=node('div');form.className='feature-form';p.append(form);let data=await call('/api/v1/catalog');
  const choose=select(form,'Editar ou adicionar',[['','Novo dispositivo'],...data.house.devices.map(d=>[d.id,d.name])]);
  const id=field(form,'ID do dispositivo'),name=field(form,'Nome');const room=select(form,'Cômodo',data.house.rooms.map(r=>[r.id,r.name]));
  const kind=select(form,'Tipo',[['light','Luz'],['switch','Tomada'],['temperature_sensor','Sensor de temperatura'],['energy_sensor','Medidor de energia cumulativa']]);
  const source=select(form,'Origem',[['simulation','Simulador'],['home_assistant','Home Assistant local']]);
  const entity=field(form,'Entidade física (ex.: light.quarto)');
  const available=field(form,'Disponível no cadastro','checkbox');available.checked=true;
  const brightness=field(form,'Suporta brilho','checkbox'),color=field(form,'Suporta cor RGB','checkbox');
  choose.onchange=()=>{const d=data.house.devices.find(x=>x.id===choose.value);id.disabled=!!d;kind.disabled=!!d;source.disabled=!!d;entity.disabled=!!d;id.value=d?.id||'';name.value=d?.name||'';room.value=d?.room_id||data.house.rooms[0].id;kind.value=d?.kind||(d?.capabilities.includes('set_color')||d?.name.toLowerCase().startsWith('luz')?'light':'switch');source.value=d?.source||'simulation';entity.value=d?.entity_id||'';available.checked=d?.available??true;brightness.checked=d?.capabilities.includes('set_brightness')||false;color.checked=d?.capabilities.includes('set_color')||false;};
  btn(p,'Salvar dispositivo',async()=>{const k=kind.value,caps=k==='temperature_sensor'?['read_temperature']:k==='energy_sensor'?['read_energy']:['turn_on','turn_off',...(k==='light'&&brightness.checked?['set_brightness']:[]),...(k==='light'&&color.checked?['set_color']:[])];
   const previous=data.house.devices.find(d=>d.id===choose.value);const d={id:id.value.trim(),name:name.value.trim(),room_id:room.value,available:available.checked,capabilities:caps,source:source.value};
   if(previous?.kind||!previous)d.kind=k; // Preserve legacy type inference for existing IDs.
   if(!['temperature_sensor','energy_sensor'].includes(k))d.initial_state=previous?.initial_state||'off';if(d.source==='home_assistant')d.entity_id=entity.value.trim();
   const house=structuredClone(data.house);if(previous)house.devices=house.devices.map(x=>x.id===previous.id?d:x);else house.devices.push(d);
   data=await call('/api/v1/catalog',{revision:data.revision,house},'PUT');notify('Dispositivo salvo. Atualizando cadastro…');location.reload();});
  const rf=node('div');rf.className='feature-form';p.append(node('h3','Cômodo'),rf);
  const rc=select(rf,'Editar ou adicionar',[['','Novo cômodo'],...data.house.rooms.map(r=>[r.id,r.name])]);const ri=field(rf,'ID do cômodo'),rn=field(rf,'Nome do cômodo');rc.onchange=()=>{const r=data.house.rooms.find(x=>x.id===rc.value);ri.value=r?.id||'';rn.value=r?.name||'';ri.disabled=!!r;};
  btn(p,'Salvar cômodo',async()=>{const house=structuredClone(data.house),r={id:ri.value.trim(),name:rn.value.trim()};if(rc.value)house.rooms=house.rooms.map(x=>x.id===rc.value?r:x);else house.rooms.push(r);await call('/api/v1/catalog',{revision:data.revision,house},'PUT');location.reload();});
 }
 async function routinesUI(){
  const p=panel('routines-panel','Rotinas e horários','Rotinas executam as ações na ordem salva. Agendamento diário exige o Aether aberto; horários perdidos não são repostos.');
  const form=node('div');form.className='feature-form';p.append(form);const id=field(form,'ID da rotina (ex.: boa-noite)'),name=field(form,'Nome (ex.: Boa noite)');
  const time=field(form,'Horário diário (opcional)','time'),zone=field(form,'Fuso','text','America/Sao_Paulo'),enabled=field(form,'Ativar agendamento','checkbox');
  let actions=[];const builder=node('div');builder.className='feature-form';p.append(node('h3','Adicionar ação'),builder);
  const ds=await call('/api/v1/devices');const dev=select(builder,'Dispositivo',ds.filter(d=>d.capabilities.includes('turn_on')).map(d=>[d.id,d.name]));
  const act=select(builder,'Ação',[['turn_off','Desligar'],['turn_on','Ligar'],['set_brightness','Brilho'],['set_color','Cor RGB']]);const val=field(builder,'Valor (brilho0–100 ou RGB ex.:255,0,0)');
  const preview=node('ol');p.append(preview);
  function draw(){preview.replaceChildren();actions.forEach((a,i)=>{const li=node('li',a.device_id+' · '+a.action+' '+(a.brightness??a.color??''));btn(li,'Remover',async()=>{actions.splice(i,1);draw();});preview.append(li);});}
  btn(p,'Adicionar etapa',async()=>{const a={device_id:dev.value,action:act.value};if(a.action==='set_brightness')a.brightness=Number(val.value);if(a.action==='set_color')a.color=val.value.split(',').map(Number);actions.push(a);draw();});
  const list=node('div');p.append(list);
  async function refresh(){list.replaceChildren();for(const r of await call('/api/v1/routines')){const row=node('div');row.className='routine-row';row.append(node('p',r.name+' · '+(r.enabled&&r.time?r.time+' '+r.timezone:'sem agendamento ativo')));btn(row,'Editar',async()=>{id.value=r.id;name.value=r.name;time.value=r.time||'';zone.value=r.timezone;enabled.checked=r.enabled;actions=structuredClone(r.actions);draw();});btn(row,'Executar',async()=>{const result=await call('/api/v1/routines/'+r.id+'/run',{request_id:crypto.randomUUID()});notify('Rotina: '+result.status,result.status!=='confirmed');history.textContent=JSON.stringify(result,null,2);await render();});btn(row,'Excluir rotina',async()=>{await call('/api/v1/routines/'+r.id,undefined,'DELETE');await refresh();});list.append(row);}}
  btn(p,'Salvar rotina',async()=>{await call('/api/v1/routines/'+id.value,{id:id.value,name:name.value,actions,enabled:enabled.checked,time:time.value||null,timezone:zone.value},'PUT');await refresh();notify('Rotina salva. Pelo chat: Execute '+name.value);});
  const history=node('pre');history.className='feature-output';p.append(history);btn(p,'Ver execuções',async()=>{history.textContent=JSON.stringify(await call('/api/v1/routines/runs/history'),null,2);});await refresh();
 }
 async function energyUI(){
  const p=panel('energy-panel','Energia da sua casa','Use leituras cumulativas em kWh do mesmo medidor. Dados inseridos manualmente ficam identificados como não verificados.');const f=node('div');f.className='feature-form';p.append(f);
  const meter=field(f,'ID do medidor','text','medidor-casa'),value=field(f,'Leitura cumulativa (kWh)','number'),date=field(f,'Horário com fuso','text',new Date().toISOString());value.step='0.001';value.min='0';
  btn(p,'Registrar leitura manual',async()=>{await call('/api/v1/energy/readings',{request_id:crypto.randomUUID(),meter_id:meter.value,timestamp:date.value,cumulative_kwh:Number(value.value)});notify('Leitura manual registrada; origem não verificada.');});
  const out=node('div');out.className='feature-output';p.append(out);btn(p,'Consultar consumo e estimativa',async()=>{const r=await call('/api/v1/energy/summary?meter_id='+encodeURIComponent(meter.value));out.replaceChildren();if(r.status==='insufficient_data'){out.append(node('p',r.message));return;}out.append(node('h3','Consumo no intervalo: '+r.observed_consumption_kwh.toLocaleString('pt-BR')+' kWh'),node('p',new Date(r.window_start).toLocaleString('pt-BR')+' até '+new Date(r.window_end).toLocaleString('pt-BR')+' · horário deste navegador'),node('p','Estimativa para uma hora após a última leitura: '+r.next_hour_estimate_kwh.toLocaleString('pt-BR')+' kWh'),node('p','Base: taxa média de '+r.samples+' amostras. Estimativa ainda sem validação preditiva.'),node('p',r.sources.includes('manual_unverified')?'Inclui dados manuais não verificados.':'Leituras obtidas pelo Home Assistant local.'),node('p',r.fresh_within_15_minutes?'Última amostra nos últimos15 minutos.':'Amostra antiga: atualize antes de usar a estimativa.'));});
 }
 async function hardwareUI(){
  const p=panel('hardware-panel','Conexão física local','Cadastre entidades do seu Home Assistant. URL e token ficam no ambiente do servidor; não são enviados ao navegador.');
  const out=node('p');p.append(out);const check=async()=>{const s=await call('/api/v1/hardware/status');out.textContent=s.message;};btn(p,'Verificar conexão',check);
  const ds=(await call('/api/v1/devices')).filter(d=>d.source==='home_assistant');const sel=select(p,'Entidade cadastrada',ds.map(d=>[d.id,d.name]));btn(p,'Sincronizar leitura física',async()=>{if(!sel.value)throw Error('Cadastre um dispositivo físico primeiro.');await call('/api/v1/hardware/sync/'+sel.value,{});await render();notify('Leitura física sincronizada.');});
  await check();
 }
 async function voiceUI(){
  const form=document.getElementById('ai-form'),voice=node('section');voice.className='aether-voice';voice.setAttribute('aria-label','Voz do Aether');form.after(voice);
  const header=node('div');header.className='voice-heading';header.append(node('strong','Voz do Aether'),node('span','ÁUDIO LOCAL'));voice.append(header);
  const row=node('div');row.className='voice-actions';voice.append(row);const state=node('p');state.className='voice-status';state.setAttribute('role','status');voice.append(state);
  const settings=node('details');settings.className='voice-settings';settings.append(node('summary','Preferências de voz'));const controls=node('div');controls.className='voice-options';settings.append(controls);voice.append(settings);
  let readiness=await call('/api/v1/voice/status');state.textContent=(readiness.recognition_ready?'Microfone local preparado.':'Voz não preparada: execute preparar_voz.py.')+' '+(readiness.speech_ready?'Resposta falada disponível.':'');
  let recorder=null,stream=null,timer=null,chunks=[],audio=null,audioUrl=null;
  let generation=0,controller=null,lastAnswer='';
  const saved=(key,fallback)=>{try{return localStorage.getItem(key)??fallback;}catch{return fallback;}};
  const save=(key,value)=>{try{localStorage.setItem(key,value);}catch{}};
  const autoLabel=node('label','Falar respostas automaticamente '),auto=node('input');auto.type='checkbox';auto.checked=saved('aether-auto-speak','on')==='on';autoLabel.className='voice-toggle';autoLabel.append(auto);controls.append(autoLabel);
  const profile=select(controls,'Estilo da voz',[['cinema','Aether cinematográfico'],['natural','Natural']]);profile.value=saved('aether-voice-profile','cinema');
  const hint=node('p','Voz padrão local. A voz de referência está fora desta rodada de testes.');hint.className='voice-hint';settings.append(hint);
  if(!profile.value)profile.value='natural';
  function stopSpeech(){generation++;controller?.abort();controller=null;if(audio){audio.pause();audio.removeAttribute('src');audio.load();audio=null;}if(audioUrl){URL.revokeObjectURL(audioUrl);audioUrl=null;}}
  auto.onchange=()=>{save('aether-auto-speak',auto.checked?'on':'off');if(!auto.checked)stopSpeech();};
  profile.onchange=()=>{save('aether-voice-profile',profile.value);stopSpeech();state.textContent='Estilo aplicado à próxima resposta. Usa a voz local instalada.';};
  async function speak(text){
   if(!text?.trim())throw Error('Envie uma mensagem primeiro.');
   readiness=await call('/api/v1/voice/status');
   if(!readiness.speech_ready)throw Error('O mecanismo de voz selecionado não está preparado.');
   if(recorder?.state==='recording')throw Error('Termine a gravação antes de ouvir.');
   stopSpeech();const current=generation;controller=new AbortController();
   state.textContent='Preparando resposta falada…';
   try{
    const r=await fetch('/api/v1/voice/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text.slice(0,1500)}),signal:controller.signal});
    if(!r.ok){const data=await r.json();throw Error(data.detail||'Não foi possível preparar o áudio.');}
    const blob=await r.blob();if(current!==generation)return;
    audioUrl=URL.createObjectURL(blob);audio=new Audio(audioUrl);
    // Cinematic preset gently lowers pitch and pace; it does not clone a film voice.
    audio.playbackRate=profile.value==='cinema'?0.94:1;audio.preservesPitch=profile.value!=='cinema';
    audio.onended=()=>{if(current===generation){stopSpeech();state.textContent='Resposta falada concluída.';}};
    await audio.play();if(current===generation)state.textContent=text.length>1500?'Lendo o início da resposta; o texto completo está no painel.':'Aether falando…';
   }catch(e){if(current!==generation||e.name==='AbortError')return;stopSpeech();state.textContent=e.name==='NotAllowedError'?'O navegador bloqueou o áudio automático. Clique em Ouvir resposta para liberar a reprodução.':e.message;}
  }
  form.addEventListener('submit',()=>{stopSpeech();lastAnswer='';},true);
  window.addEventListener('aether:answer',e=>{lastAnswer=e.detail?.answer||'';if(auto.checked&&lastAnswer)speak(lastAnswer).catch(e=>{state.textContent=e.message;});});
  const record=btn(row,'Gravar voz',async()=>{
   if(recorder?.state==='recording'){recorder.stop();return;}
   readiness=await call('/api/v1/voice/status');
   if(!readiness.recognition_ready)throw Error('Prepare Whisper local primeiro; veja o guia da versão.');
   if(!navigator.mediaDevices||!window.MediaRecorder)throw Error('Gravação não suportada. Use navegador atualizado em HTTPS ou localhost.');
   stopSpeech();stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];
   try{recorder=new MediaRecorder(stream);}catch(e){stream.getTracks().forEach(t=>t.stop());throw e;}
   recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
   recorder.onstop=async()=>{clearTimeout(timer);stream.getTracks().forEach(t=>t.stop());record.disabled=true;record.textContent='Transcrevendo…';try{const r=await fetch('/api/v1/voice/transcribe',{method:'POST',headers:{'Content-Type':recorder.mimeType||'audio/webm'},body:new Blob(chunks,{type:recorder.mimeType})});const data=await r.json();if(!r.ok)throw Error(data.detail);document.getElementById('ai-question').value=data.text;state.textContent=data.notice;}catch(e){state.textContent=e.message;}finally{chunks=[];record.disabled=false;record.textContent='Gravar voz';}};
   recorder.start();record.textContent='Parar gravação';state.textContent='Gravando, até 30 segundos. Ao terminar, revise o texto antes de enviar.';timer=setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},30000);
  });
  record.classList.add('primary');
  btn(row,'Ouvir resposta',async()=>{await speak(lastAnswer);});
  btn(row,'Parar áudio',async()=>{stopSpeech();state.textContent='Áudio interrompido.';});
  window.addEventListener('pagehide',()=>{if(recorder?.state==='recording'){recorder.onstop=null;recorder.stop();}if(stream)stream.getTracks().forEach(t=>t.stop());stopSpeech();});
 }
 async function init(){for(const fn of [voiceUI,catalogUI,routinesUI,energyUI,hardwareUI]){try{await fn();}catch(e){notify('Uma seção não carregou: '+e.message,true);}}}
 init();
})();
