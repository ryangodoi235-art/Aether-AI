"""Local Home Assistant bridge; no simulated confirmation for physical commands."""
import os,json,math,time,urllib.request,urllib.parse,ipaddress,socket
from fastapi import HTTPException

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def settings():
    url=os.environ.get('AETHER_HA_URL','').rstrip('/')
    token=os.environ.get('AETHER_HA_TOKEN','')
    if not url or not token:raise HTTPException(503,'Home Assistant não configurado. Defina AETHER_HA_URL e AETHER_HA_TOKEN.')
    p=urllib.parse.urlparse(url)
    if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password or p.path not in {'','/'}:
        raise HTTPException(503,'URL local do Home Assistant inválida.')
    try:
        ips=[ipaddress.ip_address(i[4][0]) for i in socket.getaddrinfo(p.hostname,p.port or 8123,type=socket.SOCK_STREAM)]
        if not ips or not all(i.is_private or i.is_loopback for i in ips):raise ValueError()
    except Exception:raise HTTPException(503,'Configure um endereço de rede local para o Home Assistant.')
    return url,token

def request(path,payload=None):
    url,token=settings()
    req=urllib.request.Request(url+path,data=json.dumps(payload).encode() if payload is not None else None,
         headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with opener.open(req,timeout=5) as res:raw=res.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError()
        return json.loads(raw)
    except Exception:raise HTTPException(503,'Falha na comunicação local com Home Assistant; consulte o estado antes de tentar outra ação.')

def read(d):
    row=request('/api/states/'+d['entity_id'])
    attrs=row.get('attributes',{});raw=row.get('state');available=raw not in {None,'unknown','unavailable'}
    item={**d,'source':'home_assistant','available':bool(d['available'] and available),'observed_at':row.get('last_updated'),'state':raw}
    if d.get('kind') in {'temperature_sensor','energy_sensor'}:
        try:item['value']=float(raw);assert math.isfinite(item['value'])
        except Exception:item.update(value=None,available=False)
        item['unit']=attrs.get('unit_of_measurement')
    if 'set_brightness' in d['capabilities']:
        val=attrs.get('brightness');item['brightness']=round(val*100/255) if isinstance(val,(int,float)) else None
    if 'set_color' in d['capabilities']:item['color']=attrs.get('rgb_color')
    return item

def execute(d,body):
    if body.action=='set_color' and read(d).get('state')!='on':raise HTTPException(409,'Ligue a luz física antes de alterar sua cor.')
    domain=d['entity_id'].split('.')[0]
    action=body.action
    service='turn_off' if action=='turn_off' or action=='set_brightness' and body.brightness==0 else 'turn_on'
    data={'entity_id':d['entity_id']}
    if action=='set_brightness' and body.brightness:data['brightness_pct']=body.brightness
    if action=='set_color':data['rgb_color']=list(body.color)
    request('/api/services/'+domain+'/'+service,data)
    # Readback rather than assuming an HTTP success means the device acted.
    for _ in range(3):
        actual=read(d)
        expected='off' if service=='turn_off' else 'on'
        matches=actual['available'] and actual['state']==expected
        if action=='set_brightness' and body.brightness:matches=matches and actual.get('brightness') is not None and abs(actual['brightness']-body.brightness)<=1
        if action=='set_color':matches=matches and actual.get('color')==list(body.color)
        if matches:return actual
        time.sleep(.2)
    raise HTTPException(504,'Ação enviada, mas estado físico não confirmado. Atualize antes de reenviar.')
