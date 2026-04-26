from __future__ import annotations

from threading import Lock
from typing import Dict

from models import GameSession


class InMemoryGameStore:
    def __init__(self) -> None:
        self._data: Dict[str, GameSession] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str) -> GameSession:
        with self._lock:
            if session_id not in self._data:
                self._data[session_id] = GameSession(session_id=session_id)
            return self._data[session_id]

    def get(self, session_id: str) -> GameSession | None:
        with self._lock:
            return self._data.get(session_id)

    def save(self, session: GameSession) -> None:
        with self._lock:
            self._data[session.session_id] = session


store = InMemoryGameStore()
