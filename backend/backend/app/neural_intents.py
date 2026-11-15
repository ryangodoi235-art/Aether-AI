"""The MLP classifies intent; deterministic code resolves entities and rejects unsafe scope."""
import re
from .neural_runtime import classify,normalize,NeuralError
ALIASES={'fridge':['geladeira','geladera','refrigerador'],'tv':['tv','televisao','televisor'],'ac':['ar condicionado','ar'],'shower':['chuveiro eletrico','chuveiro'],'stove':['fogao eletrico','fogao'],'microwave':['micro ondas','microondas'],'washer':['maquina de lavar','lavadora'],'lights':['lampada','luz','luminaria'],'fan':['ventilador']}
def has(text,word):return bool(normalize(word)) and re.search(r'\b'+re.escape(normalize(word))+r'\b',text) is not None

def decision(text,context,history):
 phrase=normalize(text);result=classify(text)
 def out(mode='clarify',action='none',answer='',**kw):
  return dict(mode=mode,action=action,kind=kw.get('kind'),room_id=kw.get('room_id'),device_id=kw.get('device_id'),name=kw.get('name'),answer=answer)
 if re.search(r'\b(nao|nunca|evite|cancelar|cancele|esqueca)\b',phrase):return out(answer='Nenhuma ação será executada. Pode esclarecer ou enviar um novo pedido?')
 rooms=context.get('rooms',[]);devices=context.get('devices',[]);scope=context.get('target','maquette')
 # Exact dynamic room matching, not fixed model classes for room names.
 matches=[r for r in rooms if has(phrase,r['name']) or has(phrase,r['id'])]
 if matches:
  length=max(len(normalize(r['name'])) for r in matches)
  matches=[r for r in matches if len(normalize(r['name']))==length]
 kinds=[k for k,names in ALIASES.items() if any(has(phrase,name) for name in names)]
 intent=result['intent']
 # A room-only reply can complete an immediately preceding inclusion clarification.
 if len(matches)==1 and phrase in {normalize(matches[0]['name']),normalize(matches[0]['id']),'na '+normalize(matches[0]['name']),'no '+normalize(matches[0]['name'])} and history:
  last=history[-1]
  if last['assistant'].startswith('Em qual cômodo deseja adicionar'):
   previous=classify(last['user']);prior=normalize(last['user']);prior_kinds=[k for k,names in ALIASES.items() if any(has(prior,name) for name in names)]
   if previous['intent']=='add_device' and previous['accepted'] and len(prior_kinds)==1:intent='add_device';result=previous;kinds=prior_kinds
 if intent in {'add_device','turn_on','turn_off','remove_device','add_room','remove_room'}:
  if re.search(r'\b(como|se|talvez|exemplo|suponha|explique|explicar|ensina)\b',phrase) or any(c in text for c in ['"','“','”']):return out(answer='Entendi uma explicação ou hipótese. Nenhuma ação foi proposta; reformule se deseja alterar a maquete.')
  if re.search(r'\b(e|depois|tambem|junto)\b',phrase):return out(answer='Envie uma ação por vez para conferir cada alteração antes de confirmar.')
  if not result['accepted']:return out(answer='A rede neural não identificou este pedido com pontuação suficiente. Informe a ação, o aparelho e o cômodo, ou use os controles.')
  if scope=='devices' and intent not in {'turn_on','turn_off'}:return out(answer='Neste destino posso propor ligar ou desligar dispositivos cadastrados. Para editar a residência fictícia, selecione Maquete.')
  if intent=='add_room':
   m=re.search(r'\bchamad[oa]\s+(.+)$',text,re.I) or re.search(r'\b(?:nome|ambiente|c[oô]modo|divis[aã]o)\s+(.+)$',text,re.I)
   if not m:return out(answer='Qual será o nome do novo cômodo? Use, por exemplo, “crie um cômodo chamado Escritório”.')
   return out(mode='action',action=intent,name=m.group(1).strip(' .?!')[:50])
  if len(matches)!=1:return out(answer=('Em qual cômodo deseja adicionar o aparelho?' if intent=='add_device' else 'Qual é o cômodo exato?')+' Opções: '+', '.join(r['name'] for r in rooms)+'.')
  room=matches[0]
  if intent=='remove_room':return out(mode='action',action=intent,room_id=room['id'])
  if len(kinds)!=1:return out(answer='Qual aparelho você quer alterar? Informe um tipo e um cômodo por vez.')
  kind=kinds[0]
  if intent=='add_device':return out(mode='action',action=intent,kind=kind,room_id=room['id'])
  if scope=='devices':
   candidates=[d for d in devices if d.get('room_id')==room['id'] and (has(phrase,d.get('name','__')) or any(has(normalize(d.get('name','')),a) for a in ALIASES[kind])) and intent in d.get('capabilities',[])]
  else:candidates=[d for d in devices if d.get('kind')==kind and d.get('room_id')==room['id']]
  if len(candidates)!=1:return out(answer='Não encontrei um único aparelho compatível nesse cômodo. Se houver aparelhos repetidos, use os controles para selecionar o item.')
  return out(mode='action',action=intent,device_id=candidates[0]['id'],room_id=room['id'],kind=kind)
 if intent=='energy':
  value=context.get('monthly_kwh');cost=context.get('monthly_cost')
  if isinstance(value,(int,float)) and isinstance(cost,(int,float)):
   active=[d for d in devices if d.get('on')];catalog=context.get('catalog',{});rank=sorted(active,key=lambda d:catalog.get(d.get('kind'),{}).get('watts',0)*d.get('hours',0),reverse=True)
   names=', '.join(catalog.get(d.get('kind'),{}).get('name',d.get('kind','aparelho')) for d in rank[:3])
   return out(mode='answer',answer=f'No cenário fictício configurado: {value:.2f} kWh/mês e R$ {cost:.2f}. '+('Os maiores usos ilustrativos ativos são '+names+'. ' if names else 'Não há aparelhos ativos. ')+'A previsão neural de uma hora está no laboratório e usa um histórico sintético separado; não comprova economia na residência.')
  return out(mode='answer',answer='Não há histórico horário compatível neste cadastro para uma previsão neural. A maquete usa cálculos declarados; o laboratório demonstra a rede com dados fictícios separados.')
 if intent=='deny':return out(answer='Nenhuma alteração foi proposta. Pode enviar outro pedido quando desejar.')
 return out(mode='answer',answer='A rede local reconheceu uma pergunta ou conversa fora dos comandos disponíveis. Este módulo neural pequeno classifica intenções; para explicações abertas, ative o Ollama local opcional. Ele não é um gerador de respostas gerais.')
