"""HTTP client for Rocky's ESP32 API."""

import requests

DEFAULT_ROBOT_URL = "http://192.168.4.1"
TIMEOUT = 5


class RockyClient:
    def __init__(self, base_url: str = DEFAULT_ROBOT_URL):
        self.base_url = base_url.rstrip("/")

    def status(self) -> dict:
        r = requests.get(f"{self.base_url}/api/status", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def command(self, cmd: str | None = None, face: str | None = None) -> dict:
        payload = {}
        if cmd:
            payload["command"] = cmd
        if face:
            payload["face"] = face
        if not payload:
            return {"status": "error", "message": "No command or face specified"}
        r = requests.post(
            f"{self.base_url}/api/command",
            json=payload,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()

    def move(self, direction: str) -> dict:
        return self.command(cmd=direction)

    def face(self, face: str) -> dict:
        return self.command(face=face)

    def stop(self) -> dict:
        return self.command(cmd="stop")
