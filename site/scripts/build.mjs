import {cp,mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.resolve(site,'../backend/frontend');
await access(path.join(source,'index.html'));
const output=path.join(site,'dist');
await mkdir(output,{recursive:true});
await cp(source,output,{recursive:true});
for(const file of ['login.html','cloud-entry.js','projetos.html'])await cp(path.join(site,'public',file),path.join(output,file));
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
 content=content.replace(/<\/body>/i, '<div style="position:fixed;top:0;left:0;right:0;z-index:99999;background:#181231;color:#fff;text-align:center;font:12px sans-serif;padding:6px">Demonstração online · sessão individual temporária · sensores fictícios · arquivos de planta em JSON</div></body>');
 if(!content.includes('sessão individual temporária'))content+='<div style="padding:12px;background:#181231;color:white">Demonstração online · sessão individual temporária · sensores fictícios · plantas em JSON</div>';
 await writeFile(file,content);
}
let features=await readFile(path.join(source,'features.js'),'utf8');
features=features.replace('[voiceUI,catalogUI,routinesUI,energyUI,hardwareUI]','[]');
await writeFile(path.join(output,'features.js'),features);
let sceneHTML=await readFile(path.join(output,'maquette.html'),'utf8');
sceneHTML=sceneHTML.replace('</head>','<style>#export-pdf,#export-dxf,label:has(#import-dxf),details:has(#pdf-file){display:none!important}</style></head>');
await writeFile(path.join(output,'maquette.html'),sceneHTML);

// Cloud demo does not expose unported CAD/PDF conversion controls.
await writeFile(path.join(output,'plantas_home.js'),'');
await writeFile(path.join(output,'plantas-home.js'),'');
console.log('Interface atual e páginas de cópias preparadas em site/dist.');
