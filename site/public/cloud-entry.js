(async()=>{
 try{
  const response=await fetch('/api/session',{cache:'no-store'});
  if(response.status===401){location.replace('/login.html');return;}
  if(!response.ok)return;
  const link=document.createElement('a');link.href='/projetos.html';link.textContent='Exportar cópias da sessão';
  link.className='ae-copies';
  (document.querySelector('.sidebar')||document.body).append(link);
  for(const anchor of document.querySelectorAll('a[href]'))if(/#(automation-panel|forecast-panel|routines-panel|catalog-panel|energy-panel)$/.test(anchor.getAttribute('href')))anchor.hidden=true;
  for(const panel of document.querySelectorAll('#automation-panel,#forecast-panel,#routines-panel,#catalog-panel,#energy-panel')){const section=panel.closest('details')||panel;section.hidden=true;}

 }catch{/* The existing UI reports API connection errors. */}
})();
