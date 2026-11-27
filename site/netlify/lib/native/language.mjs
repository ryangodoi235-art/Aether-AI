import {norm,CATALOG} from './domain.mjs';
const names={fridge:['geladeira','geladera','refrigerador'],tv:['televisao','tv','televisor'],ac:['ar condicionado','arcondicionado'],shower:['chuveiro eletrico','chuveiro'],stove:['fogao eletrico','fogao'],microwave:['microondas','micro ondas'],washer:['maquina de lavar','lavadora'],lights:['luz','lampada','luminaria'],fan:['ventilador']};
export function interpret(text,s){const normalized=norm(text).replace(/\b(marquete|marquete|makete)\b/g,'maquete');const phrase=normalized.replace(/^(?:(?:oi |ola )?aether |por favor |voce pode |pode |poderia |quero |quero que voce |gostaria de |gostaria que voce )+/,'').replace(/ por favor$/,'');
 const denied=/\b(nao|nunca|talvez|se|como|explique|exemplo|suponha|evite|sem)\b/.test(phrase)||/["“”]/.test(text);
 const action=/^(adicione|adicionar|adicona|coloque|inserir|inclua|incluir|bote|crie|criar)\b/.test(phrase)?'add':/^(desligue|desligar|desliga|apague|apagar)\b/.test(phrase)?'off':/^(ligue|ligar|liga|acenda|acender)\b/.test(phrase)?'on':/^(remova|remover|retire|tirar|exclua|excluir)\b/.test(phrase)?'remove':null;
 const kinds=Object.entries(names).filter(([,v])=>v.some(a=>(' '+phrase+' ').includes(' '+a+' '))).map(([k])=>k);
 const all=s.rooms.filter(r=>(' '+phrase+' ').includes(' '+norm(r.name)+' ')),rooms=all.filter(r=>!all.some(other=>other.id!==r.id&&norm(other.name).length>norm(r.name).length&&(' '+norm(other.name)+' ').includes(' '+norm(r.name)+' ')));
 return {phrase,denied,action,kinds,rooms,compound:/\b(e|depois|tambem|junto)\b/.test(phrase)};
}
