import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.ml.inference import ModelUnavailableError

class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'test.db';self.client=TestClient(create_app(db_path=self.db))
        self.body={**self.client.get('/api/v1/forecasts/demo-inputs').json()[0]['envelope'],'request_id':'forecast-1'}
    def test_real_prediction_persisted_and_idempotent(self):
        first=self.client.post('/api/v1/forecasts',json=self.body)
        self.assertEqual(first.status_code,200,first.text);data=first.json();self.assertGreater(data['prediction_kwh'],0)
        self.assertEqual(self.client.post('/api/v1/forecasts',json=self.body).json(),data)
        self.client=TestClient(create_app(db_path=self.db))
        self.assertEqual(self.client.get('/api/v1/forecasts').json(),[data])
        self.assertEqual(data['data_origin'],'historical_dataset')
        self.assertEqual(data['target_start'],self.body['as_of'])
    def test_conflict(self):
        self.client.post('/api/v1/forecasts',json=self.body)
        self.body['history'][0]['energy_kwh']+=1
        self.assertEqual(self.client.post('/api/v1/forecasts',json=self.body).status_code,409)
    def test_bad_history(self):
        self.body['history'].pop()
        self.assertEqual(self.client.post('/api/v1/forecasts',json=self.body).status_code,422)
        self.assertEqual(self.client.get('/api/v1/forecasts').json(),[])
    def test_other_origin_rejected(self):
        self.body['dataset_id']='simulation'
        self.assertEqual(self.client.post('/api/v1/forecasts',json=self.body).status_code,422)
    def test_missing_model_house_still_operates(self):
        with patch('backend.app.forecast_service.load_model',side_effect=ModelUnavailableError('missing')),patch('backend.app.ml.forecast_adapter.predict_next_hour',side_effect=ModelUnavailableError('missing')):
            self.assertEqual(self.client.get('/api/v1/forecasts/status').json()['status'],'unavailable')
            self.assertEqual(self.client.post('/api/v1/forecasts',json=self.body).status_code,503)
            self.assertEqual(self.client.get('/api/v1/devices').status_code,200)
            r=self.client.post('/api/v1/commands',json=dict(request_id='on',device_id='luz-sala',action='turn_on'))
            self.assertEqual(r.status_code,200)
    def test_text_and_no_device_change(self):
        q=dict(request_id='text1',text='Qual o consumo previsto?')
        self.assertEqual(self.client.post('/api/v1/text',json=q).json()['status'],'no_reading')
        before=self.client.get('/api/v1/devices').json();self.client.post('/api/v1/forecasts',json=self.body)
        r=self.client.post('/api/v1/text',json=q).json();self.assertEqual(r['status'],'answered');self.assertIn('histórica',r['message'])
        self.assertEqual(self.client.get('/api/v1/devices').json(),before)
    def test_status_and_panel(self):
        self.assertEqual(self.client.get('/api/v1/forecasts/status').json()['status'],'ready')
        self.assertIn('forecast-panel',self.client.get('/painel').text)
        self.assertEqual(self.client.get('/api/v1/forecasts?limit=0').status_code,422)
