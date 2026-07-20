from typing import Callable, Optional
from pathlib import Path

from ..core.logger import get_logger
from ..core.db.database_sync import init_db

from ..sessions.manager import SessionManager
from ..store.memory import MemoryStateStore
from ..sessions.session import ChatSession

log = get_logger(__name__)


class WS:
    def __init__(self, store_type: str = "memory"):
        """Initialize the WebSocket transport layer."""
        init_db()
        
        if store_type.startswith("memory"):
            self.store = MemoryStateStore()
        # elif store_type.startswith("sql"):
        #     self.store = SqlStateStore()
        else:
            raise ValueError(f"Unknown store type: {store_type}")
        
        self.session_manager = SessionManager(self.store)
        log.info(f"WS transport initialized with {store_type} store")

    def create_session(self, user_id: int | str, interpreter: "Interpreter") -> ChatSession:
        """Create and start a new chat session."""
        session = self.session_manager.create(user_id, interpreter)
        log.info(f"Created session {session.session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID. Returns None if not found or dead."""
        if not session_id:
            return None
        
        session = self.session_manager.get(session_id)
        
        # Check if the thread is actually alive
        if session and not session._thread.is_alive():
            log.warning(f"Session {session_id} found but thread is dead, cleaning up")
            self.remove_session(session_id)
            return None
        
        return session

    def remove_session(self, session_id: str) -> bool:
        """Stop and remove a session. Returns True if it existed."""
        return self.session_manager.remove(session_id)

    def validate(self, session_id: str) -> Optional[int | str]:
        """
        Validate a session exists and return the user_id.
        Returns None if invalid.
        """
        session = self.get_session(session_id)
        if session:
            return session.user_id
        return None

    def shutdown(self):
        """Stop all active sessions. Call on app shutdown."""
        log.info("Shutting down WS transport...")
        self.session_manager.shutdown()
        log.info("WS transport shut down")

    def active_count(self) -> int:
        """Return number of active sessions."""
        return self.session_manager.active_count()

    def cleanup_user_script_sessions(self, user_id: str | int, script_name: str):
        """Remove any existing sessions for this user+script combo."""
        count = self.session_manager.remove_by_user_and_script(user_id, script_name)
        if count > 0:
            log.warning(f"Cleaned up {count} stale session(s) for user {user_id} on script '{script_name}'")
