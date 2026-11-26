(async()=>{
 try{
  const response=await fetch('/api/session',{cache:'no-store'});
  if(response.status===401){location.replace('/login.html');return;}
  if(!response.ok)return;
  const link=document.createElement('a');link.href='/projetos.html';link.textContent='Exportar cópias da sessão';
  Object.assign(link.style,{position:'fixed',bottom:'16px',right:'16px',zIndex:10000,background:'#4220a0',color:'#fff',padding:'10px 16px',borderRadius:'12px',fontFamily:'sans-serif',textDecoration:'none'});
  document.body.append(link);
 }catch{/* The existing UI reports API connection errors. */}
})();
