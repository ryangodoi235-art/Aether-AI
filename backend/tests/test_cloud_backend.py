"""Exercise the protected app and its real SQLite/neural/maquette integrations."""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class CloudBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.token = 'test-only-cloud-token-' + 'a' * 40
        self.env = patch.dict(os.environ, {
            'AETHER_API_TOKEN': self.token,
            'AETHER_DATA_DIR': str(self.folder),
            'AETHER_LOCAL_NLU': '1',
            'AETHER_GENERAL_LLM': '0',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.cloud = importlib.import_module('backend.app.cloud')
        self.client = TestClient(self.cloud.create_cloud_app())
        self.headers = {'X-Aether-Token': self.token}

    def test_api_and_docs_are_private_health_does_not_leak_secrets(self):
        for path in ['/api/v1/maquette', '/api/v1/assistant/history', '/docs', '/openapi.json', '/painel']:
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.get('/api/v1/maquette', headers={'X-Aether-Token': 'incorrect'}).status_code, 401)
        self.assertEqual(self.client.get('/api/v1/maquette', params={'token': self.token}).status_code, 401)
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn(self.token, response.text)
        self.assertNotIn(str(self.folder), response.text)
        self.assertEqual(self.client.get('/api/v1/deployment/status', headers=self.headers).json()['multiuser_isolation'], False)

    def test_maquette_mutation_idempotency_and_restart_persistence(self):
        scene = self.client.get('/api/v1/maquette', headers=self.headers).json()
        ident = scene['devices'][0]['id']
        body = {'request_id': 'cloud-state-test', 'project': scene['model'],
                'revision': scene['revision'], 'op': 'device', 'data': {'id': ident, 'on': True}}
        first = self.client.post('/api/v1/maquette/action', headers=self.headers, json=body)
        self.assertEqual(first.status_code, 200, first.text)
        retry = self.client.post('/api/v1/maquette/action', headers=self.headers, json=body)
        self.assertEqual(first.json(), retry.json())
        restarted = TestClient(self.cloud.create_cloud_app())
        after = restarted.get('/api/v1/maquette', headers=self.headers).json()
        self.assertTrue(next(d for d in after['devices'] if d['id'] == ident)['on'])
        self.assertEqual(after['revision'], first.json()['revision'])
        self.assertEqual(self.client.post('/api/v1/maquette/action', headers=self.headers,
                         json={**body, 'request_id': 'stale-revision'}).status_code, 409)
        catalog = json.loads((self.folder / 'house.json').read_text())
        catalog['name'] = 'Catálogo preservado após reiniciar'
        (self.folder / 'house.json').write_text(json.dumps(catalog))
        again = TestClient(self.cloud.create_cloud_app())
        self.assertEqual(again.get('/api/v1/house', headers=self.headers).json()['name'], catalog['name'])

    def test_simulation_neural_chat_and_energy_plan_work_without_ollama(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Network not allowed')):
            status = self.client.get('/api/v1/assistant/status', headers=self.headers)
            self.assertEqual(status.status_code, 200)
            self.assertEqual(status.json()['status'], 'ready')
            self.assertFalse(status.json()['general_ollama_optional'])
            for path in ['/api/v1/maquette/sensors', '/api/v1/energy-coach/profile', '/api/v1/neural/status']:
                result = self.client.get(path, headers=self.headers)
                self.assertEqual(result.status_code, 200, (path, result.text))
            before = self.client.get('/api/v1/maquette', headers=self.headers).json()
            reply = self.client.post('/api/v1/assistant/chat', headers=self.headers,
                        json={'text': 'Olá', 'target': 'maquette', 'session_id': 'cloud-test'})
            self.assertEqual(reply.status_code, 200, reply.text)
            self.assertTrue(reply.json()['answer'])
            self.assertFalse(reply.json()['actions_executed'])
            self.assertEqual(before, self.client.get('/api/v1/maquette', headers=self.headers).json())
        voice = self.client.get('/api/v1/voice/status', headers=self.headers).json()
        self.assertFalse(voice['speech_ready'])
        self.assertFalse(voice['recognition_ready'])

    def test_missing_token_refuses_startup_and_invalid_port_is_rejected(self):
        with patch.dict(os.environ, {'AETHER_API_TOKEN': ''}):
            with self.assertRaises(RuntimeError):
                self.cloud.create_cloud_app()
        for value in ['short', 'a' * 31, 'a ' * 40, 'á' * 40, 'a' * 513]:
            with self.assertRaises(RuntimeError):
                self.cloud.validated_token(value)
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'serve_cloud.py')],
                                env={**os.environ, 'PORT': 'not-a-port'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('PORT', result.stderr)
        self.assertNotIn(self.token, result.stderr)

    def test_pdf_and_dxf_exports_include_real_generated_files(self):
        pdf = self.client.get('/api/v1/maquette/files/export.pdf', headers=self.headers)
        self.assertEqual(pdf.status_code, 200, pdf.text[:100] if pdf.status_code != 200 else '')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertIn('application/pdf', pdf.headers['content-type'])
        dxf = self.client.get('/api/v1/maquette/files/export.dxf', headers=self.headers)
        self.assertEqual(dxf.status_code, 200, dxf.text[:100])
        self.assertIn('AETHER_ROOMS', dxf.text)


if __name__ == '__main__':
    unittest.main()
