"""REST API of the climate monitoring system (FastAPI).

Run (from the backend folder):
    uvicorn main:app --host 0.0.0.0 --port 8000

API documentation (Swagger) is generated automatically: http://<address>:8000/docs
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Deque, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from hardware import get_hardware

SAMPLE_SECONDS = 10  # how often a measurement is saved to the history
HISTORY_SIZE = 500  # how many measurements to keep

hw = get_hardware()
history: Deque[dict] = deque(maxlen=HISTORY_SIZE)
state = {"threshold": 28.0}  # temperature threshold, °C


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def take_measurement() -> dict:
    """Reads the sensor and returns a dictionary with the readings."""
    reading = hw.read()
    if reading is None:
        raise HTTPException(status_code=503, detail="The sensor is not returning data yet")
    temperature, humidity = reading
    return {
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": _now(),
    }


async def sampler() -> None:
    """Background task: every SAMPLE_SECONDS it saves a measurement to the history."""
    while True:
        try:
            history.append(await asyncio.to_thread(take_measurement))
        except HTTPException:
            pass  # sensor temporarily unavailable - skip this tick
        await asyncio.sleep(SAMPLE_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sampler())
    yield
    task.cancel()
    hw.set_device(False)  # safely switch the load off when the server stops
    hw.cleanup()


app = FastAPI(
    title="Climate Monitor API",
    description="Temperature and humidity monitoring and device (relay) control on a Raspberry Pi.",
    version="1.0.0",
    lifespan=lifespan,
)


class Sensors(BaseModel):
    temperature: float = Field(description="Temperature, °C")
    humidity: float = Field(description="Relative humidity, %")
    device_on: bool = Field(description="Whether the controlled device is on")
    threshold: float = Field(description="Temperature threshold, °C")
    alert: bool = Field(description="True if the temperature is above the threshold")
    timestamp: str = Field(description="Time of the measurement (UTC, ISO 8601)")


class Measurement(BaseModel):
    temperature: float
    humidity: float
    timestamp: str


class DeviceState(BaseModel):
    device_on: bool


class ThresholdIn(BaseModel):
    value: float = Field(ge=-40, le=80, description="New temperature threshold, °C")


class ThresholdOut(BaseModel):
    threshold: float


@app.get("/status", summary="Check that the server is running")
def get_status() -> dict:
    return {"status": "ok", "mock": hw.is_mock}


@app.get("/sensors", response_model=Sensors, summary="Current readings")
def get_sensors() -> Sensors:
    m = take_measurement()
    return Sensors(
        **m,
        device_on=hw.device_on,
        threshold=state["threshold"],
        alert=m["temperature"] > state["threshold"],
    )


@app.get("/history", response_model=List[Measurement], summary="Measurement history")
def get_history(limit: int = Query(20, ge=1, le=HISTORY_SIZE)) -> List[dict]:
    """The last `limit` measurements, oldest first."""
    return list(history)[-limit:]


@app.get("/device", response_model=DeviceState, summary="Device state")
def get_device() -> DeviceState:
    return DeviceState(device_on=hw.device_on)


@app.post("/device/on", response_model=DeviceState, summary="Turn the device on")
def device_on() -> DeviceState:
    hw.set_device(True)
    return DeviceState(device_on=hw.device_on)


@app.post("/device/off", response_model=DeviceState, summary="Turn the device off")
def device_off() -> DeviceState:
    hw.set_device(False)
    return DeviceState(device_on=hw.device_on)


@app.get("/threshold", response_model=ThresholdOut, summary="Current temperature threshold")
def get_threshold() -> ThresholdOut:
    return ThresholdOut(threshold=state["threshold"])


@app.put("/threshold", response_model=ThresholdOut, summary="Set the temperature threshold")
def set_threshold(body: ThresholdIn) -> ThresholdOut:
    state["threshold"] = body.value
    return ThresholdOut(threshold=state["threshold"])
