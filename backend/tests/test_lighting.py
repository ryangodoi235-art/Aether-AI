import sqlite3
import json
import test_api

class LightingTests(test_api.ApiTests):
    def setUp(self):
        super().setUp()
        self.config['devices'][0]['capabilities'] += ['set_brightness','set_color']
        self.client = self.build()

    def extra(self, action, request_id='extra', **kwargs):
        return self.client.post('/api/v1/commands',json=dict(request_id=request_id,device_id='luz-sala',action=action,**kwargs))

    def test_brightness_and_color_persist(self):
        self.assertEqual(self.extra('set_brightness',brightness=40).json()['state'],'on')
        response=self.extra('set_color','rgb',color=[12,100,255])
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.extra('set_color','rgb',color=[12,100,255]).json(),response.json())
        self.client=self.build()
        device=self.client.get('/api/v1/devices').json()[0]
        self.assertEqual((device['brightness'],device['color']),(40,[12,100,255]))
        self.assertEqual(self.extra('set_brightness','zero',brightness=0).json()['state'],'off')
        self.assertEqual(self.extra('set_color','off-rgb',color=[0,0,255]).status_code,409)

    def test_parameters(self):
        for kwargs in [dict(brightness=101),dict(brightness=-1),dict(brightness=True),dict(brightness='40'),{}]:
            self.assertEqual(self.extra('set_brightness',**kwargs).status_code,422)
        for value in [[256,0,0],[1,2],[1,2,False]]:
            self.assertEqual(self.extra('set_color',color=value).status_code,422)
        self.assertEqual(self.extra('turn_on',brightness=20).status_code,422)
        self.config['devices'][0]['capabilities']=['turn_on','turn_off']
        self.client=self.build()
        self.assertEqual(self.extra('set_brightness',brightness=40).status_code,422)

    def test_legacy_migration_and_retry(self):
        self.db.unlink()
        payload=dict(request_id='old',device_id='luz-sala',action='turn_on')
        result=dict(payload,status='confirmed',state='on')
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE states (id TEXT PRIMARY KEY,state TEXT NOT NULL)')
            con.execute("INSERT INTO states VALUES ('luz-sala','on')")
            con.execute('CREATE TABLE commands (id TEXT PRIMARY KEY,payload TEXT NOT NULL,code INTEGER NOT NULL,result TEXT NOT NULL)')
            con.execute('INSERT INTO commands VALUES (?,?,?,?)',('old',json.dumps(payload,sort_keys=True),200,json.dumps(result)))
        self.client=self.build()
        self.assertEqual(self.send('old').json(),result)
        self.assertEqual(self.client.get('/api/v1/devices').json()[0]['state'],'on')
        self.assertEqual(self.extra('set_brightness',brightness=35).status_code,200)
