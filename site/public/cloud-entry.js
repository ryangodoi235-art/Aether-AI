(async()=>{
 try{
  const response=await fetch('/api/session',{cache:'no-store'});
  if(response.status===401){location.replace('/conta.html');return;}
  if(!response.ok)return;
  const link=document.createElement('a');link.href='/projetos.html';link.textContent='Exportar cópias da sessão';
  link.className='ae-copies';
  (document.querySelector('.sidebar')||document.body).append(link);
  const user=await fetch('/api/account/me',{cache:'no-store'});if(user.status===401){location.replace('/conta.html');return;}
  if(user.ok){const data=await user.json(),nav=document.createElement('div');nav.className='ae-account-nav';nav.textContent=data.persistent?'Conta: '+data.username:'Demonstração temporária';const account=document.createElement('a');account.href='/conta.html';account.textContent=data.persistent?'Gerenciar acesso':'Salvar em uma conta permanente';const logout=document.createElement('button');logout.type='button';logout.textContent='Sair';logout.onclick=async()=>{const r=await fetch('/api/session',{method:'DELETE'});if(r.ok)location.replace('/conta.html');};nav.append(account,logout);(document.querySelector('.sidebar')||document.body).append(nav);}
  for(const anchor of document.querySelectorAll('a[href]'))if(/#(automation-panel|forecast-panel|routines-panel|catalog-panel|energy-panel)$/.test(anchor.getAttribute('href')))anchor.hidden=true;
  for(const panel of document.querySelectorAll('#automation-panel,#forecast-panel,#routines-panel,#catalog-panel,#energy-panel')){const section=panel.closest('details')||panel;section.hidden=true;}

 }catch{/* The existing UI reports API connection errors. */}
})();
