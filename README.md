# Climate Monitor — room climate monitoring with remote control

1. Participants:
   - Махмуд Моаз Осама (Mahmoud Moaz Osama) — @DelsinRegge
2. Project topic: a room climate monitoring system with remote control from a mobile app.
3. Tasks:
   - Develop a Raspberry Pi module that reads temperature and humidity (DHT22 sensor) and controls a load (relay/LED).
   - Implement a REST API with FastAPI: current readings, measurement history, turning the device on and off, setting the temperature threshold.
   - Create an Android app (Java): a screen with current readings, device control buttons, and a warning when the temperature exceeds the threshold.
   - Test the system and write documentation for the API and for running the project.
4. Expected result by December 2026: a working prototype on a Raspberry Pi, an Android app, a documented API (Swagger), automated tests and a short testing report.
5. Link: https://github.com/DelsinRegge/climate-monitor

---

## Architecture

```
 DHT22 (temperature, humidity) ──┐
                                 ├── Raspberry Pi: FastAPI (backend/) ──Wi-Fi/HTTP──► Android app (android/)
 Relay / LED ◄───────────────────┘
```

The Raspberry Pi is the server itself, so no separate server is needed.
Without a Raspberry Pi the backend runs in simulation (mock) mode with drifting fake values.

## Repository structure

| Folder / file | Contents |
|---|---|
| `backend/main.py` | REST API (FastAPI) |
| `backend/hardware.py` | DHT22 and relay on a Raspberry Pi + a simulation for a laptop |
| `backend/test_api.py` | automated API tests (pytest) |
| `android/` | Android app source (Java) and build instructions |
| `docs/prompts.md` | prompts to generative models used in this work |
| `docs/study-guide.md` | study guide for the author |
| `docs/defense-qa.md` | likely defense questions with short answers |

## REST API

Interactive documentation (Swagger) is available at `http://<address>:8000/docs`.

| Method | Path | Description |
|---|---|---|
| GET | `/status` | the server is running; `mock: true` means simulation mode |
| GET | `/sensors` | temperature, humidity, device state, threshold, `alert` flag |
| GET | `/history?limit=20` | latest measurements (one every 10 s, up to 500) |
| GET | `/device` | device state |
| POST | `/device/on` | turn the device on |
| POST | `/device/off` | turn the device off |
| GET | `/threshold` | current temperature threshold |
| PUT | `/threshold` | set the threshold: `{"value": 28.0}` |

Example response of `GET /sensors`:

```json
{
  "temperature": 24.3,
  "humidity": 45.1,
  "device_on": false,
  "threshold": 28.0,
  "alert": false,
  "timestamp": "2026-11-07T15:30:00+00:00"
}
```

## Running the backend on a computer (simulation mode)

Windows (PowerShell):

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Linux / macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs and try the requests.

## Running on a Raspberry Pi

1. Connect the hardware (BCM numbering):
   - DHT22: data — GPIO4 (physical pin 7), power — 3.3 V, ground — GND
     (a bare 4-pin sensor needs a 10 kΩ pull-up resistor between data and power).
   - Relay or LED (through a 330 Ω resistor): control input — GPIO17 (physical pin 11).
2. Install the dependencies and start the server:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r requirements-pi.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. In the app, enter the address of the Raspberry Pi: `http://<Pi IP address>:8000`.

To force the simulation on any device, set the environment variable `MOCK=1`.

## Testing

```bash
cd backend
pip install pytest httpx
MOCK=1 pytest -v        # Windows PowerShell: $env:MOCK=1; pytest -v
```

Covered: server status, readings format, turning the device on and off, threshold and alert flag,
input validation, history length limit.

## Android app

See [android/README.md](android/README.md).
