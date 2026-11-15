import test_sensor

class HistoryTests(test_sensor.SensorTests):
    def test_history_order_pagination_restart(self):
        url='/api/v1/sensors/sensor/readings'
        self.assertEqual(self.client.get(url).json()['readings'],[])
        for value in [25.5,26,24]:
            self.client.post('/api/v1/simulation/sensors/sensor/readings',json={'value':value})
        self.config['devices'].append(dict(id='other',room_id='sala',name='Other',kind='temperature_sensor',available=True,capabilities=['read_temperature']))
        self.client=self.build()
        self.client.post('/api/v1/simulation/sensors/other/readings',json={'value':30})
        r=self.client.get(url+'?limit=2').json()
        self.assertEqual(r['total'],3)
        self.assertEqual([x['value'] for x in r['readings']],[24,26])
        self.assertEqual(self.client.get(url+'?limit=2&offset=2').json()['readings'][0]['value'],25.5)
        self.assertEqual(self.client.get(url+'?offset=100').json()['readings'],[])
        self.config['devices'][-2]['available']=False
        self.client=self.build()
        r=self.client.get(url).json()
        self.assertFalse(r['available'])
        self.assertEqual(r['total'],3)
        for query in ['limit=0','limit=101','offset=-1']:
            self.assertEqual(self.client.get(url+'?'+query).status_code,422)
        self.assertEqual(self.client.get('/api/v1/sensors/missing/readings').status_code,404)
        self.assertEqual(self.client.get('/api/v1/sensors/luz-sala/readings').status_code,422)
