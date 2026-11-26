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
console.log('Interface atual e páginas de cópias preparadas em site/dist.');
