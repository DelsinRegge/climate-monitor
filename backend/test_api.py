"""Automated API tests. Run (from the backend folder): MOCK=1 pytest -v"""

import os

os.environ["MOCK"] = "1"  # tests always run on the simulation, without a Raspberry Pi

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_status():
    with TestClient(app) as client:
        r = client.get("/status")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "mock": True}


def test_sensors_fields():
    with TestClient(app) as client:
        data = client.get("/sensors").json()
        for key in ("temperature", "humidity", "device_on", "threshold", "alert", "timestamp"):
            assert key in data
        assert 15 <= data["temperature"] <= 40
        assert 20 <= data["humidity"] <= 80


def test_device_on_off():
    with TestClient(app) as client:
        assert client.post("/device/on").json() == {"device_on": True}
        assert client.get("/device").json() == {"device_on": True}
        assert client.get("/sensors").json()["device_on"] is True
        assert client.post("/device/off").json() == {"device_on": False}


def test_threshold_and_alert():
    with TestClient(app) as client:
        # threshold -39 °C: the temperature is always higher, so the alert is on
        assert client.put("/threshold", json={"value": -39}).json() == {"threshold": -39}
        assert client.get("/sensors").json()["alert"] is True
        # threshold 79 °C: the temperature is always lower, so there is no alert
        client.put("/threshold", json={"value": 79})
        assert client.get("/sensors").json()["alert"] is False


def test_threshold_validation():
    with TestClient(app) as client:
        assert client.put("/threshold", json={"value": 1000}).status_code == 422


def test_history_limit():
    with TestClient(app) as client:
        r = client.get("/history", params={"limit": 5})
        assert r.status_code == 200
        assert len(r.json()) <= 5
        assert client.get("/history", params={"limit": 0}).status_code == 422
