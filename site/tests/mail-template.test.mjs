import test from 'node:test';
import assert from 'node:assert/strict';
import {renderMail} from '../netlify/lib/mail-template.mjs';
test('confirmation code stays readable, escaped and outside links',()=>{
 const html=renderMail({subject:'Confirmação <teste>',text:'Olá, <Ryan>.\n\nSeu código de confirmação é: 012345\n\nEle vence em 10 minutos.'});
 assert.match(html,/012345/);assert.match(html,/&lt;Ryan&gt;/);assert.doesNotMatch(html,/<Ryan>/);
 assert.match(html,/aether-email-banner-v1.png/);assert.match(html,/height:auto/);
 assert.doesNotMatch(html,/href="[^"]*012345/);assert.match(html,/10 minutos/);
});
test('plan has correct destination and escapes user content',()=>{
 const html=renderMail({subject:'Seu plano',text:'Olá!\n\n<script>alert(1)</script>\nConta informada: R$ 200'});
 assert.match(html,/Ver meu plano no Aether/);assert.match(html,/href="https:\/\/aether-ai-ryan.netlify.app\/painel"/);
 assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);
 assert.match(html,/sensores simulados/);
});
