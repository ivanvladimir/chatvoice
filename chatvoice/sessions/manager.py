import logging
import threading
import uuid
from typing import Callable, Optional

from .session import ChatSession

log = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, store):
        self.store = store
        self._sessions: dict[str, ChatSession] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str | int, conversation: Callable) -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(user_id, session_id, conversation, self.store)

        with self._lock:
            # Clean up any previous session for this ID if somehow duplicated
            self._sessions[session_id] = session

        session.start()
        return session

    def get(self, session_id: str) -> Optional[ChatSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str, wait: float = 2.0) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)

        if session is None:
            return False

        session.stop()
        session.wait(timeout=wait)
        log.debug(f"Removed session {session_id}")
        return True

    def shutdown(self, wait: float = 5.0):
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        log.info(f"Shutting down {len(sessions)} sessions")
        for session in sessions:
            session.stop()
        for session in sessions:
            session.wait(timeout=wait)

    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def remove_by_user_and_script(
        self, user_id: str | int, script_name: str, wait: float = 2.0
    ) -> int:
        """
        Find and remove all active sessions for a specific user and script.
        Returns the number of sessions removed.
        """
        with self._lock:
            # Find matching session IDs
            to_remove = [
                sid
                for sid, s in self._sessions.items()
                if s.user_id == user_id and s.interpreter_name == script_name
            ]

            # Pop them from the dict
            sessions = [self._sessions.pop(sid) for sid in to_remove]

        # Stop threads OUTSIDE the lock so we don't block other operations
        count = 0
        for session in sessions:
            session.stop()
            session.wait(timeout=wait)
            count += 1

        return count
