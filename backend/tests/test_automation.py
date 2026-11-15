import json
import test_api
from fastapi.testclient import TestClient
from backend.app.main import create_app

class AutomationTests(test_api.ApiTests):
    def setUp(self):
        super().setUp()
        self.config['devices'] += [dict(id='temp',room_id='sala',name='Sensor',kind='temperature_sensor',available=True,capabilities=['read_temperature']),dict(id='outlet',room_id='sala',name='Tomada',available=True,capabilities=['turn_on','turn_off'],initial_state='off')]
        self.client=self.build()
        self.rule=dict(enabled=True,sensor_id='temp',target_id='outlet',on_at=28,off_at=26)
    def sample(self,value):
        return self.client.post('/api/v1/simulation/sensors/temp/readings',json={'value':value})
    def state(self):
        return next(d['state'] for d in self.client.get('/api/v1/devices').json() if d['id']=='outlet')
    def enable(self):
        self.assertEqual(self.client.post('/api/v1/automation',json=self.rule).status_code,200)
    def test_hysteresis_and_no_duplicates(self):
        self.sample(30); self.assertEqual(self.state(),'off')
        self.enable();self.assertEqual(self.state(),'off')
        for value,expected in [(28,'on'),(29,'on'),(27,'on'),(26,'off'),(25,'off'),(27,'off')]:
            self.assertEqual(self.sample(value).status_code,201);self.assertEqual(self.state(),expected)
        actions=[e for e in self.client.get('/api/v1/automation/events').json() if e['status']=='confirmed']
        self.assertEqual(len(actions),2)
        self.assertEqual(len(self.client.get('/api/v1/events').json()),2)
    def test_disabled_and_restart(self):
        self.enable();self.sample(30)
        self.client=TestClient(create_app(self.file,self.db))
        self.assertTrue(self.client.get('/api/v1/automation').json()['enabled'])
        self.assertEqual(self.state(),'on')
        self.client.post('/api/v1/automation',json={**self.rule,'enabled':False})
        self.sample(20);self.assertEqual(self.state(),'on')
    def test_validation(self):
        for changes in [{'off_at':28},{'on_at':101},{'sensor_id':'missing'},{'target_id':'temp'},{'enabled':'true'}]:
            self.assertEqual(self.client.post('/api/v1/automation',json={**self.rule,**changes}).status_code,422)
        self.assertEqual(self.client.get('/api/v1/automation/events').json(),[])
    def test_unavailable_target_records_failure(self):
        self.enable();self.config['devices'][-1]['available']=False;self.client=self.build()
        self.assertEqual(self.sample(30).status_code,201)
        self.assertEqual(self.client.get('/api/v1/automation/events').json()[0]['status'],'failed')
        self.assertEqual(self.client.post('/api/v1/automation',json={**self.rule,'enabled':False}).status_code,200)
    def test_other_sensor_invalid_sample_and_manual_override(self):
        self.config['devices'].append({**self.config['devices'][-2],'id':'temp2'});self.client=self.build();self.enable()
        self.client.post('/api/v1/simulation/sensors/temp2/readings',json={'value':30});self.assertEqual(self.state(),'off')
        self.assertEqual(self.sample(101).status_code,422);self.assertEqual(self.state(),'off')
        self.sample(30);self.send('manual','outlet','turn_off');self.assertEqual(self.state(),'off')
        self.sample(30);self.assertEqual(self.state(),'on')
