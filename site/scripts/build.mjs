import {cp,mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.resolve(site,'../backend/frontend');
await access(path.join(source,'index.html'));
const output=path.join(site,'dist');
await mkdir(output,{recursive:true});
await cp(source,output,{recursive:true});
for(const file of ['login.html','cloud-entry.js','projetos.html','experience.css','experience.js','voice-chat.js','conta.html','brand.js'])await cp(path.join(site,'public',file),path.join(output,file));
await cp(path.join(site,'public/brand'),path.join(output,'brand'),{recursive:true});
// The current backend interface is authoritative; the historical site copy is stale.
let html=await readFile(path.join(source,'index.html'),'utf8');
html=html.replace(/data:image\/png;base64,[A-Za-z0-9+/=]+/g,'/brand/aether-symbol.png');
html+='\n<script src="/cloud-entry.js" defer></script>\n';
await writeFile(path.join(output,'index.html'),html);
for(const [folder,file,dest] of [['maquette','app.js','maquette-assets/app.js'],['maquette','style.css','maquette-assets/style.css'],['','neural_home.js','neural-assets/home.js'],['','plantas_local.js','plantas-local.js'],['','plantas_home.js','plantas-home.js'],['','energy_home.js','energy-home.js']]){
 const target=path.join(output,dest);await mkdir(path.dirname(target),{recursive:true});await cp(path.join(source,folder,file),target);
}
// Online capability notice; local source files remain untouched.
for(const page of ['index.html','maquette.html','energy_coach.html','plantas_local.html']){
 const file=path.join(output,page);let content=await readFile(file,'utf8');
 content=content.replaceAll('Processamento local','Demonstração online').replaceAll('salvos no SQLite','salvos no MongoDB por sessão').replaceAll('Redes neurais locais','Redes neurais experimentais');
 content=content.replace(/<head([^>]*)>/i,'<head$1><script>window.AETHER_NETLIFY_NATIVE=true;</script>');
 if(page==='energy_coach.html'){
  content=content.replace('void speakPlan();',"window.parent.postMessage({type:'aether-plan-updated',answer:current.answer},location.origin);");
  content=content.replace('async function speakPlan(){',"async function speakPlan(){if(window.AETHER_NETLIFY_NATIVE){if(window.parent!==window)window.parent.postMessage({type:'aether-speak-plan',answer:current?.answer||''},location.origin);feedback('Selecione a voz em Conversar por voz, no chat da Home.');return;}");
  content=content.replace("$('stop-plan-audio').onclick=()=>{stopAudio();", "$('stop-plan-audio').onclick=()=>{window.parent.postMessage({type:'aether-stop-voice'},location.origin);stopAudio();");
 }
 const view=page==='index.html'?'home':page==='maquette.html'?'maquette':page==='energy_coach.html'?'plan':'files';
 content=content.replace(/<html\b/i,'<html data-aether-view="'+view+'"');
 content+='\n<link rel="stylesheet" href="/experience.css"><script src="/experience.js" defer></script><script src="/voice-chat.js" defer></script>\n';
 await writeFile(file,content);
}
let features=await readFile(path.join(source,'features.js'),'utf8');
features=features.replace('[voiceUI,catalogUI,routinesUI,energyUI,hardwareUI]','[]');
await writeFile(path.join(output,'features.js'),features);
let sceneHTML=await readFile(path.join(output,'maquette.html'),'utf8');
sceneHTML=sceneHTML.replace('</head>','<style>#export-pdf,#export-dxf,label:has(#import-dxf),details:has(#pdf-file){display:none!important}</style></head>');
await writeFile(path.join(output,'maquette.html'),sceneHTML);

// Cloud demo does not expose unported CAD/PDF conversion controls.
// The scene already caps device pixel ratio and renders on demand. Pause sensor polling
// in inactive tabs as well, without changing the bundled Three.js internals.
const sceneJS=path.join(output,'maquette-assets/app.js');
let sceneCode=await readFile(sceneJS,'utf8');
if(!sceneCode.includes('setInterval(Eu,5e3)'))throw Error('Scene polling changed; review the visibility guard.');
sceneCode=sceneCode.replace('setInterval(Eu,5e3)','setInterval(()=>{if(!document.hidden)Eu()},5e3)');
await writeFile(sceneJS,sceneCode);
await writeFile(path.join(output,'plantas_home.js'),'');
await writeFile(path.join(output,'plantas-home.js'),'');
console.log('Interface atual e páginas de cópias preparadas em site/dist.');

// Apply the identity to entry screens too, without changing form IDs or API contracts.
const brandHead='<link rel="icon" type="image/png" href="/brand/aether-symbol.png"><meta name="theme-color" content="#080e1c">';
for(const page of ['index.html','maquette.html','energy_coach.html','plantas_local.html','neural_lab.html','login.html','conta.html','projetos.html']){
 const file=path.join(output,page);let content=await readFile(file,'utf8');
 content=content.replace(/<head([^>]*)>/i,'<head$1>'+brandHead);
 if(!content.includes('href="/experience.css"'))content+='\n<link rel="stylesheet" href="/experience.css">';
 content+='\n<script src="/brand.js" defer></script>';
 await writeFile(file,content);
}
