import uuid
from typing import Callable
import threading

from .session import ChatSession


class SessionManager:
    def __init__(self, store):
        self.store = store
        self._sessions: dict[tuple[str, str, str], ChatSession] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, conversation: Callable) -> ChatSession:
        # Always creates a new session — caller gets back the session_id
        # to reference it later (send messages, close it, etc.)
        session_id = str(uuid.uuid4())
        key = (user_id, conversation.name, session_id)
        session = ChatSession(user_id, session_id, conversation, self.store)
        with self._lock:
            self._sessions[key] = session
        session.start()
        return session

    def get(self, user_id: str, conversation_name: str, session_id: str) -> ChatSession | None:
        key = (user_id, conversation_name, session_id)
        with self._lock:
            return self._sessions.get(key)

    def remove(self, user_id: str, conversation_name: str, session_id: str):
        key = (user_id, conversation_name, session_id)
        with self._lock:
            self._sessions.pop(key, None)

    def sessions_for_user(self, user_id: str) -> list[ChatSession]:
        with self._lock:
            return [s for (uid, _, _), s in self._sessions.items() if uid == user_id]
