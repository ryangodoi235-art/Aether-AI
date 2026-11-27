import test from 'node:test';
import assert from 'node:assert/strict';
import {access,readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
test('publication includes actual frontend, login, Mongo UI and every local script',async()=>{
 execFileSync(process.execPath,['scripts/build.mjs'],{cwd:site});
 const generated=await readFile(path.join(site,'dist/index.html'),'utf8');
 const original=await readFile(path.join(site,'../backend/frontend/index.html'),'utf8');
 assert.ok(generated.includes('AETHER_NETLIFY_NATIVE=true'));assert.ok(generated.includes('data-aether-view="home"'));await access(path.join(site,'dist/experience.css'));await access(path.join(site,'dist/experience.js'));assert.ok(original.includes('AETHER_NETLIFY_NATIVE')===false);
 for(const page of ['index.html','maquette.html','plantas_local.html']){
  const html=await readFile(path.join(site,'dist',page),'utf8');
  for(const [,src] of html.matchAll(/<script[^>]+src=["']([^"']+)/g)){
   if(!src.startsWith('/'))continue;
   await access(path.join(site,'dist',src.split('?')[0]));
  }
 }
 for(const file of ['login.html','projetos.html','maquette-assets/style.css'])await access(path.join(site,'dist',file));
 assert.ok((await readFile(path.join(site,'dist/features.js'),'utf8')).includes('for(const fn of [])'));assert.ok((await readFile(path.join(site,'../backend/frontend/features.js'),'utf8')).includes('[voiceUI,catalogUI,routinesUI,energyUI,hardwareUI]'));
});
