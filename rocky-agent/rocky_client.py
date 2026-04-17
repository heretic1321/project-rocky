"""HTTP client for Rocky's ESP32 API — used by the voice agent."""

import logging
import requests

logger = logging.getLogger("rocky.client")

TIMEOUT = 3


class RockyClient:
    def __init__(self, base_url: str = "http://192.168.4.1"):
        self.base_url = base_url.rstrip("/")

    def send(self, command: str | None = None, face: str | None = None) -> bool:
        payload = {}
        if command:
            payload["command"] = command
        if face:
            payload["face"] = face
        if not payload:
            return False
        try:
            r = requests.post(
                f"{self.base_url}/api/command",
                json=payload,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            logger.debug("Sent to Rocky: %s -> %s", payload, r.json())
            return True
        except requests.RequestException as e:
            logger.warning("Failed to send to Rocky: %s", e)
            return False

    def status(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/api/status", timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.warning("Failed to get Rocky status: %s", e)
            return None
