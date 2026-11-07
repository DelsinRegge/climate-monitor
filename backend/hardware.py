"""Hardware access: DHT22 sensor and relay/LED on a Raspberry Pi.

If the Raspberry Pi libraries are missing (for example, you run the code on a laptop)
or the environment variable MOCK=1 is set, a simulation (MockHardware) is used.
This way the API can be developed and tested without a Raspberry Pi.

Wiring on the Raspberry Pi (BCM numbering):
  - DHT22: data line -> GPIO4 (physical pin 7), power 3.3V, ground GND
  - Relay / LED (through a 330 ohm resistor): control input -> GPIO17 (physical pin 11)
"""

import os
import random
import threading
import time
from typing import Optional, Tuple

RELAY_PIN = 17  # GPIO17 (BCM) - relay or LED
DHT_GPIO_NAME = "D4"  # GPIO4 in the naming used by the "board" library

FORCE_MOCK = os.getenv("MOCK", "").lower() in ("1", "true", "yes")

try:
    if FORCE_MOCK:
        raise ImportError("MOCK mode requested")
    import adafruit_dht  # type: ignore
    import board  # type: ignore
    import RPi.GPIO as GPIO  # type: ignore

    ON_PI = True
except (ImportError, NotImplementedError, RuntimeError):
    ON_PI = False


class MockHardware:
    """Simulated sensor and relay: temperature and humidity drift slowly."""

    is_mock = True

    def __init__(self) -> None:
        self._temp = 24.0
        self._hum = 45.0
        self._device_on = False
        self._lock = threading.Lock()

    def read(self) -> Optional[Tuple[float, float]]:
        with self._lock:
            self._temp += random.uniform(-0.4, 0.4)
            self._hum += random.uniform(-1.0, 1.0)
            self._temp = max(15.0, min(40.0, self._temp))
            self._hum = max(20.0, min(80.0, self._hum))
            return round(self._temp, 1), round(self._hum, 1)

    def set_device(self, on: bool) -> None:
        with self._lock:
            self._device_on = on

    @property
    def device_on(self) -> bool:
        return self._device_on

    def cleanup(self) -> None:
        pass


class PiHardware:
    """Real hardware: DHT22 + relay through RPi.GPIO."""

    is_mock = False

    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
        self._dht = adafruit_dht.DHT22(getattr(board, DHT_GPIO_NAME))
        self._last: Optional[Tuple[float, float]] = None
        self._device_on = False
        self._lock = threading.Lock()

    def read(self) -> Optional[Tuple[float, float]]:
        # The DHT22 sometimes fails to read - this is normal, so we try again.
        for _ in range(3):
            try:
                temp = self._dht.temperature
                hum = self._dht.humidity
                if temp is not None and hum is not None:
                    self._last = (round(temp, 1), round(hum, 1))
                    break
            except RuntimeError:
                time.sleep(2.0)
        return self._last  # None if no reading has succeeded yet

    def set_device(self, on: bool) -> None:
        with self._lock:
            GPIO.output(RELAY_PIN, GPIO.HIGH if on else GPIO.LOW)
            self._device_on = on

    @property
    def device_on(self) -> bool:
        return self._device_on

    def cleanup(self) -> None:
        GPIO.output(RELAY_PIN, GPIO.LOW)
        GPIO.cleanup()
        self._dht.exit()


def get_hardware():
    """Returns PiHardware on a Raspberry Pi and MockHardware everywhere else."""
    return PiHardware() if ON_PI else MockHardware()
