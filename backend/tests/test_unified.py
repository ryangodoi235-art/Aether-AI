import unittest
from unittest.mock import patch
from test_text import TextTests

class UnifiedTests(unittest.TestCase):
    build=TextTests.build
    setUp=TextTests.setUp
    def say(self,text,rid=None):
        body={'text':text}
        if rid:body['request_id']=rid
        return self.client.post('/api/v1/assistant/chat',json=body)
    def test_color_requires_light_then_confirms(self):
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            failed=self.say('Deixe a luz do quarto vermelha').json()
            self.assertEqual(failed['status'],'failed');self.assertFalse(failed['actions_executed'])
            self.assertIn('Ligue a luz',failed['answer'])
            self.assertTrue(self.say('Aether, ligue a luz do quarto').json()['actions_executed'])
            result=self.say('Aether deixa a luz do quarto vermelha').json()
            self.assertTrue(result['actions_executed']);self.assertEqual(result['command']['color'],[255,0,0])
            self.assertEqual(next(d for d in result['context']['devices'] if d['id']=='luz-quarto')['color'],[255,0,0])
    def test_ambiguity_invalid_negative_compound(self):
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            for text in ['Ligue a luz', 'Não ligue a luz da sala', 'Ligue a luz da sala e desligue a luz do quarto','Coloque o brilho do quarto em 101%', 'Ligue a luz da cozinha']:
                r=self.say(text).json();self.assertFalse(r['actions_executed'],text)
        self.assertEqual(self.client.get('/api/v1/events').json(),[])
    def test_retry_conflict_restart_history(self):
        r=self.say('Ligue a luz do quarto','retry-id').json()
        self.assertEqual(self.say('Ligue a luz do quarto','retry-id').json(),r)
        self.assertEqual(len(self.client.get('/api/v1/events').json()),1)
        self.assertEqual(len(self.client.get('/api/v1/assistant/history').json()),1)
        self.assertEqual(self.say('Desligue a luz do quarto','retry-id').status_code,409)
        self.client=self.build()
        self.assertEqual(self.say('Ligue a luz do quarto','retry-id').json(),r)
    def test_capability_availability_and_sensor(self):
        self.assertFalse(self.say('Coloque o brilho da sala em 40%').json()['actions_executed'])
        self.config['devices'][1]['available']=False;self.client=self.build()
        self.assertEqual(self.say('Ligue a luz do quarto').json()['status'],'failed')
        self.client.post('/api/v1/simulation/sensors/sensor/readings',json={'value':26.5})
        r=self.say('Qual é a temperatura da sala?').json()
        self.assertIn('26.5',r['answer']);self.assertFalse(r['actions_executed'])
    def test_temperature_exact_saved_timestamp_long_question(self):
        import sqlite3
        self.client.post('/api/v1/simulation/sensors/sensor/readings',json={'value':26.5})
        timestamp='2026-10-07T21:49:11.322119+00:00'
        with sqlite3.connect(self.db) as con:
            con.execute('UPDATE temperature_readings SET timestamp=?',(timestamp,))
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('Temperature must not reach model')):
            for phrase in ['Qual foi a última temperatura registrada na sala e em que horário?',
                           'Qual é a última temperatura da sala?', 'Qual foi a temperatura medida na sala e quando foi medida?',
                           'Qual é a temperatura da sala?', 'Aether, qual foi a última temperatura registrada na sala e em que horário?']:
                r=self.say(phrase).json()
                self.assertEqual(r['response_source'],'backend_query',r)
                self.assertIn(timestamp,r['answer']);self.assertIn('26.5',r['answer'])
                self.assertNotIn('2010-',r['answer']);self.assertFalse(r['actions_executed'])
        self.assertEqual(self.client.get('/api/v1/events').json(),[])
    def test_temperature_no_reading_unknown_room_and_unavailable(self):
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            self.assertEqual(self.say('Qual foi a última temperatura registrada na sala e em que horário?').json()['status'],'no_reading')
            self.assertEqual(self.say('Qual foi a última temperatura registrada na cozinha e em que horário?').json()['status'],'needs_clarification')
            self.config['devices'][-1]['available']=False;self.client=self.build()
            r=self.say('Qual foi a última temperatura registrada na sala e em que horário?').json()
            self.assertEqual(r['status'],'failed');self.assertIn('indispon',r['answer'].lower())
    def test_temperature_ambiguous_multiple_rooms(self):
        self.config['devices'].append(dict(self.config['devices'][-1],id='sensor-quarto',name='Temperatura do quarto',room_id='quarto'))
        self.client=self.build()
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            r=self.say('Qual foi a última temperatura registrada e em que horário?').json()
            self.assertEqual(r['status'],'needs_clarification');self.assertFalse(r['actions_executed'])
    def test_unrecognized_temperature_phrase_does_not_invent(self):
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            r=self.say('Você acompanha a temperatura continuamente?').json()
            self.assertEqual(r['response_source'],'backend_temperature_guidance')
            self.assertIn('não há monitoramento contínuo',r['answer'])
            self.assertFalse(r['actions_executed'])
