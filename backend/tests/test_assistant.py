import unittest
from unittest.mock import patch
import test_api

class AssistantTests(unittest.TestCase):
    build=test_api.ApiTests.build
    setUp=test_api.ApiTests.setUp
    def test_context_persistence_no_actions(self):
        client=self.build()
        before=client.get('/api/v1/devices').json()
        fake={'done':True,'done_reason':'stop','message':{'content':'A luz está desligada.'}}
        with patch('backend.app.assistant_service.ollama',return_value=fake) as call:
            r=client.post('/api/v1/assistant/chat',json={'text':'Explique o objetivo do Aether'})
            self.assertEqual(r.status_code,200)
            data=r.json();self.assertFalse(data['actions_executed'])
            payload=call.call_args.args[1]
            self.assertEqual(payload['model'],'qwen2.5:3b')
            self.assertIn('simulation',payload['messages'][1]['content'])
            self.assertEqual(data['context']['historical_forecast']['status'],'no_reading')
        self.assertEqual(client.get('/api/v1/devices').json(),before)
        self.assertEqual(client.get('/api/v1/events').json(),[])
        again=self.build().get('/api/v1/assistant/history').json()
        self.assertEqual(again[0]['answer'],'A luz está desligada.')
    def test_unavailable_and_invalid(self):
        c=self.build()
        with patch('backend.app.assistant_service.ollama',side_effect=TimeoutError):
            self.assertEqual(c.get('/api/v1/assistant/status').json()['status'],'unavailable')
            self.assertEqual(c.post('/api/v1/assistant/chat',json={'text':'Oi'}).status_code,503)
            self.assertEqual(c.get('/api/v1/devices').status_code,200)
        for fake in [{'done':True,'done_reason':'length','message':{'content':'parcial'}},
                     {'done':True,'done_reason':'stop','message':{'content':''}},
                     {'done':True,'done_reason':'stop','message':{'content':'<think>oops'}},
                     {'done':True,'done_reason':'stop','message':{'content':'ok','tool_calls':[{}]}}]:
            with patch('backend.app.assistant_service.ollama',return_value=fake):
                self.assertEqual(c.post('/api/v1/assistant/chat',json={'text':'Oi'}).status_code,502)
        self.assertEqual(c.get('/api/v1/assistant/history').json(),[])
    def test_status_and_validation(self):
        c=self.build()
        with patch('backend.app.assistant_service.ollama',return_value={'models':[]}):
            self.assertEqual(c.get('/api/v1/assistant/status').json()['status'],'model_missing')
        with patch('backend.app.assistant_service.ollama',return_value={'models':[{'name':'qwen2.5:3b'}]}):
            self.assertEqual(c.get('/api/v1/assistant/status').json()['status'],'ready')
        for text in [' ', 'a'*801]:
            self.assertEqual(c.post('/api/v1/assistant/chat',json={'text':text}).status_code,422)

    def test_commands_execute_without_model(self):
        c=self.build()
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model expected')):
            r=c.post('/api/v1/assistant/chat',json={'text':'Ligue a luz da sala.'}).json()
            self.assertTrue(r['actions_executed'])
            self.assertEqual(r['command']['state'],'on')
            self.assertEqual(r['response_source'],'backend_command')
        self.assertEqual(c.get('/api/v1/devices').json()[0]['state'],'on')

    def test_false_claim_is_replaced(self):
        c=self.build()
        for answer in ['A luz da sala foi ligada.', 'A luz vermelha no quarto foi acionada.', 'Eu liguei a luz.']:
            with patch('backend.app.assistant_service.ollama',return_value={'done':True,'done_reason':'stop','message':{'content':answer}}):
                r=c.post('/api/v1/assistant/chat',json={'text':'Explique o objetivo do Aether'})
                self.assertEqual(r.json()['response_source'],'backend_claim_guard')
                self.assertNotEqual(r.json()['answer'],answer)
    def test_forecast_facts_not_rewritten(self):
        from backend.app.assistant_service import controlled_reply
        snap={'historical_forecast':{'forecast':{'prediction_kwh':0.523,'target_start':'2010-04-22T05:00:00','target_end':'2010-04-22T06:00:00'}}}
        answer,source=controlled_reply('Explique a última previsão salva',snap)
        self.assertEqual(source,'backend_forecast')
        self.assertIn('0.523 kWh',answer)
        self.assertIn('2010-04-22T05:00:00',answer)
        self.assertIn('previsão de consumo',answer)
        self.assertIn('sem atribuição a um cômodo',answer)
        self.assertIn('Não é geração',answer)
        c=self.build()
        with patch('backend.app.assistant_service.ollama',side_effect=AssertionError('No model')):
            r=c.post('/api/v1/assistant/chat',json={'text':'Qual o consumo atual?'})
            self.assertEqual(r.status_code,200)
            self.assertIn('não dispõe de medição',r.json()['answer'])
