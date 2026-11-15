"""Deterministic read-only device questions, resolved against the full registry."""
import re,unicodedata

def norm(s):return ' '.join(''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').strip(' .?!').split())

def reply(text,devices,rooms):
    q=norm(text);q=re.sub(r'^aether[, ]+','',q)
    list_query=re.fullmatch(r'(?:quais|quantos) (dispositivos|luzes|lampadas|tomadas)(?: estao| estao agora)? (ligados|ligadas|desligados|desligadas|disponiveis|indisponiveis)(?: (?:na|no|da|do|em) (.+))?',q)
    singular=re.fullmatch(r'(?:qual (?:e )?(?:o |a )?(estado|brilho|cor|disponibilidade)(?: (?:da|do|de))? (.+)|(?:a |o )?(.+?) esta (ligada|ligado|desligada|desligado|disponivel|indisponivel))',q)
    state_all=q in {'como estao os dispositivos da casa','como esta a casa','estado da casa','quais dispositivos existem na casa'}
    if not (list_query or singular or state_all):
        if re.search(r'\b(brilho|cor|ligad[oa]s?|desligad[oa]s?|dispositivos|tomadas|lampadas)\b',q) and not re.search(r'\b(ligue|desligue|deixe|coloque|ajuste|defina|acenda|apague|liga|desliga|deixa|nao)\b',q):
            return 'Para consultar os dados exatos, pergunte por exemplo “Quais dispositivos estão ligados?” ou “Qual é o brilho da luz do quarto?”.', 'backend_devices'
        return None,None
    selected=list(devices)
    def light(d):return d.get('kind')=='light' or bool(re.match(r'(luz|lampada)\b',norm(d['name'])))
    if list_query:
        kind,state,room=list_query.groups()
        if room and room not in {"casa","minha casa","toda a casa"}:
            matches=[r['id'] for r in rooms if norm(r['id'])==room or norm(r['name'])==room]
            if len(matches)!=1:return 'Cômodo não encontrado ou ambíguo. Informe seu nome completo.','backend_devices'
            selected=[d for d in selected if d['room_id']==matches[0]]
        if kind in {'luzes','lampadas'}:selected=[d for d in selected if light(d)]
        elif kind=='tomadas':selected=[d for d in selected if d.get('kind')=='switch' or norm(d['name']).startswith('tomada')]
        if state in {'disponiveis','indisponiveis'}:selected=[d for d in selected if d['available']==(state=='disponiveis')]
        else:selected=[d for d in selected if d['available'] and d.get('state')==('off' if state.startswith('deslig') else 'on')]
        return ('Resultado do cadastro/estado observado: '+str(len(selected))+'. '+('; '.join(d['name'] for d in selected) if selected else 'Nenhum dispositivo corresponde à consulta.')+' Dados simulados ou Home Assistant, conforme a origem de cada dispositivo.','backend_devices')
    if singular:
        field,target,target2,asked=singular.groups();target=target or target2;field=field or 'estado'
        selected=[d for d in selected if target in {norm(d['id']),norm(d['id'].replace('-',' ')),norm(d['name'])} or (target in {'luz','lampada'} and light(d))]
        if len(selected)!=1:return 'Informe o nome completo: '+('; '.join(d['name'] for d in selected) if selected else 'dispositivo não encontrado')+'.','backend_devices'
        d=selected[0];prefix=d['name']+' ('+('físico via Home Assistant' if d['source']=='home_assistant' else 'simulação')+'): '
        if field=='disponibilidade':return prefix+('disponível.' if d['available'] else 'indisponível; estado não confirmado.'),'backend_devices'
        if not d['available']:return prefix+'indisponível; não há estado atual confirmado.','backend_devices'
        if field in {'brilho','cor'}:
            cap='set_brightness' if field=='brilho' else 'set_color';key='brightness' if field=='brilho' else 'color'
            if cap not in d['capabilities']:return prefix+'não suporta '+field+'.','backend_devices'
            v=d.get(key)
            return prefix+(('brilho '+str(v)+'%') if field=='brilho' else 'cor RGB '+str(v)) +'.' if v is not None else prefix+field+' ainda não definido.','backend_devices'
        return prefix+({'on':'ligado','off':'desligado'}.get(d.get('state'),'sem estado ligar/desligar'))+'.','backend_devices'
    return ('Estados por dispositivo: '+'; '.join(d['name']+': '+('indisponível' if not d['available'] else {'on':'ligado','off':'desligado'}.get(d.get('state'),'sensor com amostras'))+' ['+d['source']+']' for d in selected)+'.','backend_devices')
