import uuid
from typing import Callable
import threading

from .session import ChatSession


class SessionManager:
    def __init__(self, store):
        self.store = store
        self._sessions: dict[str, ChatSession] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, conversation: Callable) -> ChatSession:
        # Always creates a new session — caller gets back the session_id
        # to reference it later (send messages, close it, etc.)
        session_id = str(uuid.uuid4())
        key = session_id
        session = ChatSession(user_id, session_id, conversation, self.store)
        with self._lock:
            self._sessions[key] = session
        session.start()
        return session

    def get(self, session_id: str) -> ChatSession | None:
        key = session_id
        with self._lock:
            session=self._sessions.get(key, None)
            if session:
                return session

    def remove(self, session_id: str):
        key = session_id
        with self._lock:
            self._sessions.pop(key, None)
