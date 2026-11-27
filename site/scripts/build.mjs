import {cp,mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.resolve(site,'../backend/frontend');
await access(path.join(source,'index.html'));
const output=path.join(site,'dist');
await mkdir(output,{recursive:true});
await cp(source,output,{recursive:true});
for(const file of ['login.html','cloud-entry.js','projetos.html','experience.css','experience.js'])await cp(path.join(site,'public',file),path.join(output,file));
// The current backend interface is authoritative; the historical site copy is stale.
let html=await readFile(path.join(source,'index.html'),'utf8');
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
 const view=page==='index.html'?'home':page==='maquette.html'?'maquette':page==='energy_coach.html'?'plan':'files';
 content=content.replace(/<html\b/i,'<html data-aether-view="'+view+'"');
 content+='\n<link rel="stylesheet" href="/experience.css"><script src="/experience.js" defer></script>\n';
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
