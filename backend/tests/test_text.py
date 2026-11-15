import test_api
import unittest

class TextTests(unittest.TestCase):
    build = test_api.ApiTests.build
    def setUp(self):
        test_api.ApiTests.setUp(self)
        self.config['rooms'].append({'id':'quarto','name':'Quarto'})
        self.config['devices'].append(dict(id='luz-quarto',name='Luz do quarto',room_id='quarto',available=True,initial_state='off',capabilities=['turn_on','turn_off','set_brightness','set_color']))
        self.config['devices'].append(dict(id='sensor',name='Temperatura da sala',room_id='sala',available=True,kind='temperature_sensor',capabilities=['read_temperature']))
        self.client=self.build()
    def say(self,text,id='text-1'):
        return self.client.post('/api/v1/text',json={'request_id':id,'text':text}).json()
    def test_actions_and_retry(self):
        first=self.say('Ligue a luz da sala.')
        self.assertEqual(first['status'],'confirmed')
        self.assertEqual(self.say('Ligue a luz da sala.')['command'],first['command'])
        self.assertEqual(self.say('Desligue a luz da sala.')['status'],'failed')
        self.assertEqual(self.say('Coloque o brilho do quarto em 50%','b')['command']['brightness'],50)
        self.assertEqual(self.say('Deixe a luz do quarto na cor azul','c')['command']['color'],[0,0,255])
    def test_no_partial_execution(self):
        for phrase in ['Não ligue a luz da sala','Ligue a luz da sala e desligue a luz do quarto','Ligue a luz','Ligue a luz da cozinha','Coloque o brilho do quarto em 101%']:
            self.assertNotEqual(self.say(phrase)['status'],'confirmed')
        self.assertEqual(self.client.get('/api/v1/events').json(),[])
    def test_capability_and_reading(self):
        self.assertEqual(self.say('Coloque o brilho da sala em 50%')['status'],'failed')
        self.assertEqual(self.say('Qual é a temperatura da sala?')['status'],'no_reading')
        self.client.post('/api/v1/simulation/sensors/sensor/readings',json={'value':27})
        self.assertEqual(self.say('Qual é a temperatura da sala?')['reading']['value'],27)
