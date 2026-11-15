import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.voice import setup
class ReleaseTests(unittest.TestCase):
 def test_empty_whisper_directory_is_not_ready(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'models/whisper-tiny').mkdir(parents=True)
   app=FastAPI();setup(app,root)
   with patch('backend.app.voice.importlib.util.find_spec',return_value=object()):
    r=TestClient(app).get('/api/v1/voice/status').json()
    self.assertFalse(r['recognition_ready']);self.assertFalse(r['speech_ready'])
 def test_missing_models_reject_instead_of_fake_success(self):
  with tempfile.TemporaryDirectory() as d:
   app=FastAPI();setup(app,Path(d));c=TestClient(app)
   self.assertEqual(c.post('/api/v1/voice/speak',json={'text':'Olá'}).status_code,503)
   self.assertEqual(c.post('/api/v1/voice/transcribe',content=b'').status_code,422)
   self.assertEqual(c.post('/api/v1/voice/transcribe',content=b'audio').status_code,503)
 def test_existing_files_only_check_is_explicit(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m=root/'models/whisper-tiny';m.mkdir(parents=True)
   for f in ['model.bin','config.json','tokenizer.json']:(m/f).write_bytes(b'x')
   app=FastAPI();setup(app,root)
   with patch('backend.app.voice.importlib.util.find_spec',return_value=object()):
    r=TestClient(app).get('/api/v1/voice/status').json()
    self.assertTrue(r['recognition_ready']);self.assertIn('inferência',r['readiness_scope'])
