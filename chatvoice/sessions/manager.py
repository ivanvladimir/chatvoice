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

    def create(
        self,
        user_id: str | int,
        conversation: Callable,
        session_id: Optional[str] = None,
    ) -> ChatSession:
        session_id = session_id or str(uuid.uuid4())
        session = ChatSession(user_id, session_id, conversation, self.store)

        with self._lock:
            # Clean up any previous session for this ID if somehow duplicated
            self._sessions[session_id] = session

        session.start()
        return session

    def create_replacing(
        self,
        user_id: str | int,
        script_name: str,
        conversation: Callable,
        session_id: Optional[str] = None,
        wait: float = 2.0,
    ) -> ChatSession:
        """
        Atomically replace any existing session(s) for this (user_id,
        script_name) with a new one.

        Unlike calling remove_by_user_and_script() followed by create()
        separately, the "find stale sessions for this user+script" and
        "register the new one" steps happen under a single lock acquisition.
        That matters because the caller (establish_ws_session) does several
        `await`s (DB lookups) between wanting to clean up and actually being
        ready to register the new session -- a second, near-simultaneous
        call for the same user+script (e.g. a double form submit, a client
        retry) can otherwise interleave in that gap: both calls see "nothing
        to clean up yet" before either has registered its own session, and
        both survive as orphaned, un-cleaned-up interpreters.
        """
        session_id = session_id or str(uuid.uuid4())
        session = ChatSession(user_id, session_id, conversation, self.store)

        with self._lock:
            stale_ids = [
                sid
                for sid, s in self._sessions.items()
                if s.user_id == user_id and s.interpreter_name == script_name
            ]
            stale_sessions = [self._sessions.pop(sid) for sid in stale_ids]
            self._sessions[session_id] = session

        if stale_sessions:
            log.warning(
                f"Replacing {len(stale_sessions)} stale session(s) for user "
                f"{user_id} on script '{script_name}'"
            )
        for stale_session in stale_sessions:
            stale_session.stop()
            stale_session.wait(timeout=wait)

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

    def list_sessions(self) -> list[dict]:
        """Return info about all active sessions (for debugging/monitoring)."""
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "interpreter": s.interpreter_name,
                    "is_alive": s._thread.is_alive(),
                }
                for s in self._sessions.values()
            ]
