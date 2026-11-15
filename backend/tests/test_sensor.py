import test_api

class SensorTests(test_api.ApiTests):
    def setUp(self):
        super().setUp()
        self.config['devices'].append(dict(id='sensor',room_id='sala',name='Temperatura',kind='temperature_sensor',available=True,capabilities=['read_temperature']))
        self.client=self.build()

    def test_reading_lifecycle(self):
        url='/api/v1/sensors/sensor/reading'
        self.assertEqual(self.client.get(url).json()['status'],'no_reading')
        self.send()
        first=self.client.post('/api/v1/simulation/sensors/sensor/readings',json={'value':25.5})
        self.assertEqual(first.status_code,201)
        self.client=self.build()
        self.assertEqual(self.client.get(url).json(),first.json())
        self.assertEqual(self.client.get('/api/v1/devices').json()[0]['state'],'on')
        self.assertEqual(self.send('sensor-on',device_id='sensor').status_code,422)
        self.assertEqual(len(self.client.get('/api/v1/events').json()),2)

    def test_invalid_and_unavailable(self):
        url='/api/v1/simulation/sensors/sensor/readings'
        for value in [-51,101,True,'25']:
            self.assertEqual(self.client.post(url,json={'value':value}).status_code,422)
        self.assertEqual(self.client.get('/api/v1/sensors/unknown/reading').status_code,404)
        self.assertEqual(self.client.get('/api/v1/sensors/luz-sala/reading').status_code,422)
        self.config['devices'][-1]['available']=False
        self.client=self.build()
        self.assertEqual(self.client.get('/api/v1/sensors/sensor/reading').status_code,503)
        self.assertEqual(self.client.post(url,json={'value':25}).status_code,503)
