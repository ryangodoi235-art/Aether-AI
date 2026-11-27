(()=>{'use strict';
const page=document.documentElement.dataset.aetherView;
const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
if(page==='home'){
 const main=document.querySelector('main');if(!main)return;
 const note=make('div',null,'ae-session-note');note.append(make('strong','Seu espaço de demonstração'),document.createTextNode(' · Maquete individual por sessão. Sensores simulados. Exporte sua planta antes de encerrar o acesso.'));main.prepend(note);
 const title=document.querySelector('.hero h2,.hero h1');if(title)title.textContent='Entenda sua casa. Planeje sua economia.';
 const desc=document.querySelector('.hero-copy p');if(desc)desc.textContent='Explore a residência em 3D, teste seus aparelhos e compare hábitos de consumo.';
 const refresh=document.querySelector('#refresh');if(refresh)refresh.title='Atualizar os dados desta sessão';
 const question=document.querySelector('#ai-question');if(question)question.placeholder='Ex.: adicione uma geladeira na cozinha';
 const form=document.querySelector('#ai-form');if(form){const prompts=make('div',null,'ae-prompts');prompts.setAttribute('aria-label','Exemplos de mensagens');for(const label of ['Adicione uma geladeira na cozinha','Ligue a luz da sala','Como economizar energia?']){const b=make('button',label);b.type='button';b.onclick=()=>{question.value=label;question.focus();};prompts.append(b);}form.before(prompts);}
 const answer=document.querySelector('#ai-answer');if(answer){const placeholder=make('p','Escolha um exemplo ou escreva seu pedido. Antes de alterar a maquete, o Aether solicitará confirmação.','ae-empty');answer.before(placeholder);const observe=()=>{placeholder.hidden=!!answer.textContent.trim();};new MutationObserver(observe).observe(answer,{subtree:true,childList:true,characterData:true});observe();}
 const link=make('a','Abrir conversa','ae-mobile-chat');link.href='#ai-card';link.onclick=()=>question?.focus({preventScroll:true});main.append(link);
 const footer=make('footer','Aether AI · Projeto acadêmico · Gestão da Tecnologia da Informação. Valores de economia são projeções, não resultados comprovados.','ae-footer');main.append(footer);
 const toggle=document.querySelector('#motion-toggle');if(toggle&&!document.documentElement.classList.contains('motion-paused'))toggle.click();
 const badge=make('p','Verificando conexão da sua sessão…','ae-session-note ae-connection');badge.setAttribute('role','status');note.after(badge);
 fetch('/api/v1/database/status',{cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok)throw Error(r.status===401?'Entre novamente para carregar seu espaço.':d.detail||'Não foi possível carregar os dados.');badge.textContent='Conexão disponível · alterações salvas no MongoDB nesta sessão.';badge.dataset.state='ok';}).catch(e=>{badge.textContent=e.message;badge.dataset.state='error';});
 const copies=document.querySelector('a[href="/projetos.html"]');if(copies){copies.removeAttribute('style');copies.className='ae-copies';copies.textContent='Minhas cópias de plantas';document.querySelector('.sidebar')?.append(copies);}
}
if(page==='maquette'){
 if(window.self!==window.top)document.querySelector('header p')?.remove();
 const eyebrow=document.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='RESIDÊNCIA INTERATIVA · SIMULAÇÃO';
 const tools=document.querySelector('.toolbar');if(tools){const exportButton=document.querySelector('#export-plan');if(exportButton)exportButton.textContent='Baixar planta JSON';}
 const reference=document.querySelector('#reference-editor');if(reference)reference.hidden=true;
 const notice=document.querySelector('.metrics + p.small');if(notice)notice.textContent='Os valores abaixo estimam o cenário cadastrado. Selecione um cômodo para editar seus aparelhos; as leituras dos sensores são fictícias.';
}
})();
