import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from backend.app.main import create_app, ROOT


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.config = {"id": "test-house", "name": "Casa de teste", "rooms": [{"id": "sala", "name": "Sala"}], "devices": [{"id": "luz-sala", "room_id": "sala", "name": "Luz da sala", "available": True, "capabilities": ["turn_on", "turn_off"], "initial_state": "off"}]}
        self.file = self.path / "house.json"
        self.db = self.path / "test.db"
        self.client = self.build()

    def build(self):
        self.file.write_text(json.dumps(self.config), encoding="utf-8")
        return TestClient(create_app(self.file, self.db))

    def send(self, request_id="test-1", device_id="luz-sala", action="turn_on"):
        return self.client.post("/api/v1/commands", json={
            "request_id": request_id, "device_id": device_id, "action": action})

    def test_on_off(self):
        self.assertEqual(self.send().json()["state"], "on")
        self.assertEqual(self.send("test-2", action="turn_off").json()["state"], "off")

    def test_retry_and_conflict(self):
        first = self.send().json()
        self.assertEqual(self.send().json(), first)
        self.assertEqual(len(self.client.get("/api/v1/events").json()), 1)
        self.assertEqual(self.send(action="turn_off").status_code, 409)

    def test_missing_logged(self):
        self.assertEqual(self.send(device_id="missing").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/events").json()[0]["error"], "device_not_found")

    def test_persist_restart(self):
        self.send()
        self.client = self.build()
        self.assertEqual(self.client.get("/api/v1/devices").json()[0]["state"], "on")
        self.assertEqual(len(self.client.get("/api/v1/events").json()), 1)

    def test_new_device_config_only(self):
        self.config["rooms"].append({"id": "quarto", "name": "Quarto"})
        self.config["devices"].append({**self.config["devices"][0], "id": "nova", "room_id": "quarto"})
        self.client = self.build()
        self.assertEqual(self.send(device_id="nova").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/devices").json()[0]["state"], "off")

    def test_unavailable(self):
        self.config["devices"][0]["available"] = False
        self.client = self.build()
        self.assertEqual(self.send().status_code, 503)

    def test_unsupported(self):
        self.config["devices"][0]["capabilities"] = ["turn_off"]
        self.client = self.build()
        self.assertEqual(self.send().status_code, 422)

    def test_invalid_input(self):
        self.assertEqual(self.send(action="blue").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/events?limit=1000").status_code, 422)


if __name__ == "__main__":
    unittest.main()
