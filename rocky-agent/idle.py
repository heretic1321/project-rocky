"""Random idle behavior loop for Rocky."""

import asyncio
import logging
import random

from rocky_client import RockyClient

logger = logging.getLogger("rocky.idle")

FACE_ONLY = [
    "idle", "idle_blink", "thinking", "sleepy", "confused",
    "happy", "surprised",
]

FACE_WITH_POSE = [
    ("shake", "confused"),
    ("cute", "love"),
    ("shrug", "thinking"),
    ("point", "excited"),
    ("bow", "happy"),
]

BIG_MOVEMENTS = [
    ("dance", "dance"),
    ("swim", "happy"),
    ("worm", "excited"),
    ("wave", "happy"),
]


class IdleLoop:
    def __init__(self, client: RockyClient, min_interval: int = 10, max_interval: int = 30):
        self._client = client
        self._min = min_interval
        self._max = max_interval
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.ensure_future(self._loop())
        logger.info("Idle loop started")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Idle loop stopped")

    def pause(self):
        self._running = False
        logger.debug("Idle loop paused")

    def resume(self):
        if self._task and not self._task.done():
            self._running = True
            logger.debug("Idle loop resumed")
        else:
            self.start()

    async def _loop(self):
        while True:
            delay = random.uniform(self._min, self._max)
            await asyncio.sleep(delay)
            if not self._running:
                continue
            self._do_random_action()

    def _do_random_action(self):
        roll = random.random()
        if roll < 0.60:
            face = random.choice(FACE_ONLY)
            self._client.send(face=face)
            logger.debug("Idle: face -> %s", face)
        elif roll < 0.85:
            cmd, face = random.choice(FACE_WITH_POSE)
            self._client.send(command=cmd, face=face)
            logger.debug("Idle: pose -> %s + %s", cmd, face)
        else:
            cmd, face = random.choice(BIG_MOVEMENTS)
            self._client.send(command=cmd, face=face)
            logger.debug("Idle: big move -> %s + %s", cmd, face)
