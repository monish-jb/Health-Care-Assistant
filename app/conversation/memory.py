"""In-memory session store with TTL. Replace with Redis + encryption for production."""
import time
from collections import defaultdict

from app.core.config import get_settings


class SessionMemory:
    def __init__(self):
        self._data: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self._seen: dict[str, float] = {}

    def _expire(self):
        ttl, now = get_settings().session_ttl_seconds, time.time()
        for sid in [s for s, t in self._seen.items() if now - t > ttl]:
            self.delete(sid)

    def add(self, sid: str, role: str, text: str):
        self._expire()
        self._data[sid].append((role, text))
        self._seen[sid] = time.time()

    def history(self, sid: str) -> list[tuple[str, str]]:
        self._expire()
        return self._data.get(sid, [])[-get_settings().max_history_turns * 2:]

    def delete(self, sid: str):  # supports "delete my data" requests
        self._data.pop(sid, None)
        self._seen.pop(sid, None)


memory = SessionMemory()
