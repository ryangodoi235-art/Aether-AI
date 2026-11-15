import unittest,json,sqlite3
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import test_text

class FeaturesTests(unittest.TestCase):
    setUp=test_text.TextTests.setUp
    build=test_text.TextTests.build
    def ask(self,text,session='one',rid=None):
        import uuid
        return self.client.post('/api/v1/assistant/chat',json={'text':text,'session_id':session,'request_id':rid or uuid.uuid4().hex})
    def routine(self,**kw):
        return dict(id='boa-noite',name='Boa noite',actions=[{'device_id':'luz-sala','action':'turn_off'},{'device_id':'luz-quarto','action':'turn_off'}],enabled=False,time=None,timezone='America/Sao_Paulo',**kw)
    def test_facts_never_model_and_no_actions(self):
        self.client.post('/api/v1/commands',json={'request_id':'on','device_id':'luz-quarto','action':'turn_on'})
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            for q in ['Quais dispositivos estão ligados na casa?','Quais luzes estão desligadas?','A luz do quarto está ligada?','Qual é o brilho da luz do quarto?','Qual é a cor da luz do quarto?','Qual é a disponibilidade da luz da sala?']:
                r=self.ask(q);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['response_source'],'backend_devices');self.assertFalse(r.json()['actions_executed'])
            self.assertIn('Luz do quarto',self.ask('Quais dispositivos estão ligados?').json()['answer'])
            self.assertIn('não suporta',self.ask('Qual é o brilho da luz da sala?').json()['answer'])
        self.assertEqual(len(self.client.get('/api/v1/events').json()),1)
    def test_session_followup_isolated_persisted_and_retry(self):
        self.assertEqual(self.ask('Ligue a luz').json()['status'],'needs_clarification')
        with patch('backend.app.assistant_service.ollama',return_value={'done':True,'done_reason':'stop','message':{'content':'Informe um dispositivo.'}}):
            self.assertFalse(self.ask('A do quarto',session='two').json()['actions_executed'])
        self.client=self.build()
        r=self.ask('A do quarto',rid='follow').json();self.assertTrue(r['actions_executed']);self.assertEqual(r['command']['device_id'],'luz-quarto')
        self.assertEqual(self.ask('A do quarto',rid='follow').json(),r)
        self.assertEqual(self.ask('A do quarto',session='two',rid='follow').status_code,409)
    def test_cancel_expiration_and_disabled_pending(self):
        self.ask('Ligue a luz');self.ask('cancelar')
        self.assertEqual(len(self.client.get('/api/v1/events').json()),0)
        self.ask('Ligue a luz')
        with sqlite3.connect(self.db) as c:
            p=json.loads(c.execute("SELECT payload FROM assistant_sessions WHERE id='one'").fetchone()[0]);p['pending']['created']=0;c.execute("UPDATE assistant_sessions SET payload=? WHERE id='one'",(json.dumps(p),))
        with patch('backend.app.assistant_service.ollama',return_value={'done':True,'done_reason':'stop','message':{'content':'Reformule o pedido.'}}):
            self.assertFalse(self.ask('A do quarto').json()['actions_executed'])
        self.ask('Ligue a luz');self.config['devices'][1]['available']=False;self.client=self.build();self.assertFalse(self.ask('A do quarto').json()['actions_executed'])
    def test_catalog_live_restart_and_conflict(self):
        c=self.client.get('/api/v1/catalog').json();h=c['house'];h['rooms'].append({'id':'cozinha','name':'Cozinha'});h['devices'].append({'id':'luz-cozinha','name':'Luz da cozinha','room_id':'cozinha','available':True,'kind':'light','initial_state':'off','capabilities':['turn_on','turn_off']})
        r=self.client.put('/api/v1/catalog',json=c);self.assertEqual(r.status_code,200,r.text)
        self.assertTrue(self.ask('Ligue a luz da cozinha').json()['actions_executed'])
        self.assertEqual(self.client.put('/api/v1/catalog',json=c).status_code,409)
        from backend.app.main import create_app
        from fastapi.testclient import TestClient
        self.client=TestClient(create_app(self.file,self.db));self.assertTrue(any(d['id']=='luz-cozinha' for d in self.client.get('/api/v1/devices').json()))
    def test_catalog_duplicate_and_reference_protection(self):
        c=self.client.get('/api/v1/catalog').json();c['house']['rooms'].append(c['house']['rooms'][0]);self.assertEqual(self.client.put('/api/v1/catalog',json=c).status_code,422)
        c=self.client.get('/api/v1/catalog').json();c['house']['devices'].pop();self.assertEqual(self.client.put('/api/v1/catalog',json=c).status_code,422)
    def test_routine_chat_repeat_history(self):
        self.assertEqual(self.client.put('/api/v1/routines/boa-noite',json=self.routine()).status_code,200)
        r=self.ask('Execute Boa noite',rid='night').json();self.assertTrue(r['actions_executed']);self.assertEqual(r['routine']['status'],'confirmed')
        self.assertEqual(self.ask('Execute Boa noite',rid='night').json(),r)
        self.assertEqual(len(self.client.get('/api/v1/events').json()),2)
        self.assertEqual(len(self.client.get('/api/v1/routines/runs/history').json()),1)
    def test_routine_invalid_preflight_and_partial(self):
        r=self.routine();r['actions'][1]['action']='open_door';self.assertEqual(self.client.put('/api/v1/routines/boa-noite',json=r).status_code,422)
        r=self.routine();r['actions'][1]={'device_id':'luz-quarto','action':'set_color','color':[255,0,0]};self.client.put('/api/v1/routines/boa-noite',json=r)
        result=self.client.post('/api/v1/routines/boa-noite/run',json={'request_id':'partial'}).json();self.assertEqual(result['status'],'partial')
    def test_schedule_once_per_day_and_disabled(self):
        r=self.routine();r.update(enabled=True,time='22:00');self.client.put('/api/v1/routines/boa-noite',json=r)
        when=datetime(2026,10,19,1,0,tzinfo=timezone.utc)
        self.client.app.state.scheduler_tick(when);self.client.app.state.scheduler_tick(when)
        self.assertEqual(len(self.client.get('/api/v1/events').json()),2)
        self.client.app.state.scheduler_tick(when+timedelta(days=1));self.assertEqual(len(self.client.get('/api/v1/events').json()),4)
    def test_energy_cumulative_baseline_and_idempotency(self):
        start=datetime.now(timezone.utc)-timedelta(hours=2)
        for i in range(3):
            body={'request_id':'e'+str(i),'meter_id':'casa','timestamp':(start+timedelta(hours=i)).isoformat(),'cumulative_kwh':100+i*.4}
            self.assertEqual(self.client.post('/api/v1/energy/readings',json=body).status_code,201)
            self.assertEqual(self.client.post('/api/v1/energy/readings',json=body).status_code,201)
        r=self.client.get('/api/v1/energy/summary?meter_id=casa').json();self.assertEqual(r['observed_consumption_kwh'],.8);self.assertEqual(r['next_hour_estimate_kwh'],.4);self.assertEqual(r['sources'],['manual_unverified'])
        body.update(request_id='decrease',timestamp=(start+timedelta(hours=2,minutes=1)).isoformat(),cumulative_kwh=99)
        self.assertEqual(self.client.post('/api/v1/energy/readings',json=body).status_code,422)
        self.assertEqual(self.client.get('/api/v1/energy/summary?meter_id=missing').json()['status'],'insufficient_data')
    def test_voice_absent_and_audio_limits(self):
        with patch('backend.app.voice.importlib.util.find_spec',return_value=None):
            self.assertFalse(self.client.get('/api/v1/voice/status').json()['recognition_ready'])
            self.assertEqual(self.client.post('/api/v1/voice/speak',json={'text':'Olá'}).status_code,503)
        self.assertEqual(self.client.post('/api/v1/voice/transcribe',content=b'').status_code,422)
        self.assertEqual(self.client.post('/api/v1/voice/transcribe',content=b'x'*8_000_001).status_code,413)
    def test_hardware_missing_no_simulated_success(self):
        self.config['devices'][1].update(kind='light',source='home_assistant',entity_id='light.quarto');self.client=self.build()
        with patch('backend.app.hardware.request',side_effect=__import__('fastapi').HTTPException(503,'off')):
            ds=self.client.get('/api/v1/devices').json();d=next(d for d in ds if d['id']=='luz-quarto');self.assertFalse(d['available']);self.assertEqual(d['source'],'home_assistant')
            r=self.client.post('/api/v1/commands',json={'request_id':'physical','device_id':'luz-quarto','action':'turn_on'});self.assertEqual(r.status_code,503);self.assertEqual(r.json()['detail']['source'],'home_assistant');self.assertEqual(r.json()['detail']['status'],'failed')
    def test_hardware_readback_and_no_repeated_send(self):
        self.config['devices'][1].update(kind='light',source='home_assistant',entity_id='light.quarto');self.client=self.build()
        from backend.app import hardware
        state={'state':'off','attributes':{},'last_updated':datetime.now(timezone.utc).isoformat()};posts=[]
        def mock(path,payload=None):
            if payload is not None:posts.append(payload);state['state']='on';return []
            return state
        with patch.object(hardware,'request',side_effect=mock):
            b={'request_id':'physical','device_id':'luz-quarto','action':'turn_on'}
            self.assertEqual(self.client.post('/api/v1/commands',json=b).json()['state'],'on')
            self.client.post('/api/v1/commands',json=b);self.assertEqual(len(posts),1)
    def test_large_registry_facts_and_disclosed_context(self):
        for i in range(250):self.config['devices'].append(dict(self.config['devices'][0],id='d-'+str(i),name='Luz extra '+str(i)))
        self.client=self.build()
        with patch('backend.app.assistant_service.ollama',return_value={'done':True,'done_reason':'stop','message':{'content':'Posso explicar este resumo.'}}) as model:
            r=self.ask('Explique o objetivo do Aether').json();self.assertIsNotNone(r['context_selection']);self.assertLess(r['context_selection']['included'],253)
            self.assertLess(len(model.call_args.args[1]['messages'][1]['content']),6000)
            r=self.ask('Quantos dispositivos estão desligados?').json();self.assertIn('252',r['answer'])

    def test_hardware_energy_sync_and_unit_rejection(self):
        self.config['devices'].append({'id':'medidor','name':'Energia da casa','room_id':'sala','available':True,'kind':'energy_sensor','source':'home_assistant','entity_id':'sensor.energia','capabilities':['read_energy']});self.client=self.build()
        from backend.app import hardware
        row={'state':'100.4','attributes':{'unit_of_measurement':'kWh'},'last_updated':datetime.now(timezone.utc).isoformat()}
        with patch.object(hardware,'request',return_value=row):
            self.assertEqual(self.client.post('/api/v1/hardware/sync/medidor').status_code,200)
            self.assertEqual(self.client.post('/api/v1/hardware/sync/medidor').status_code,200)
            rows=self.client.get('/api/v1/energy/readings?meter_id=medidor').json();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source'],'home_assistant')
            row['attributes']['unit_of_measurement']='W';self.assertEqual(self.client.post('/api/v1/hardware/sync/medidor').status_code,422)
    def test_local_voice_pipeline_with_mock_engines(self):
        import os,sys,types
        from pathlib import Path
        whisper=self.path/'whisper';whisper.mkdir();piper=self.path/'voice.onnx';piper.write_bytes(b'model');piper.with_suffix('.onnx.json').write_text('{}')
        for filename in ['model.bin','config.json','tokenizer.json']:(whisper/filename).write_bytes(b'mock')
        class FakeModel:
            def __init__(self,*args,**kw):assert kw['local_files_only']
            def transcribe(self,*args,**kw):return iter([types.SimpleNamespace(text='Ligue a luz da sala')]),None
        fake=types.ModuleType('faster_whisper');fake.WhisperModel=FakeModel
        aud=types.ModuleType('faster_whisper.audio');aud.decode_audio=lambda *a,**k:[0]*16000
        with patch.dict(os.environ,{'AETHER_WHISPER_MODEL':str(whisper),'AETHER_PIPER_MODEL':str(piper)}),patch('backend.app.voice.importlib.util.find_spec',return_value=object()),patch.dict(sys.modules,{'faster_whisper':fake,'faster_whisper.audio':aud}):
            r=self.client.post('/api/v1/voice/transcribe',content=b'fake');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['text'],'Ligue a luz da sala');self.assertEqual(self.client.get('/api/v1/events').json(),[])
            def synth(args,**kw):Path(args[-1]).write_bytes(b'RIFFmock-WAVE')
            with patch('backend.app.voice.subprocess.run',side_effect=synth):
                r=self.client.post('/api/v1/voice/speak',json={'text':'Olá'});self.assertEqual(r.status_code,200);self.assertIn('audio/wav',r.headers['content-type'])
    def test_routine_sensor_action_rejected(self):
        r=self.routine();r['actions']=[{'device_id':'sensor','action':'read_temperature'}];self.assertEqual(self.client.put('/api/v1/routines/boa-noite',json=r).status_code,422)
