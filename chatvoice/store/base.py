from abc import ABC, abstractmethod


class BaseStateStore(ABC):
    @abstractmethod
    def get(self, user_id: str, conversation_name: str, session_id: str) -> dict:
        """Load state for a specific session. Returns {} if not found."""
        ...

    @abstractmethod
    def set(
        self, user_id: str, state: dict, conversation_name: str, session_id: str
    ) -> None:
        """Persist state for a specific session."""
        ...

    @abstractmethod
    def delete(self, user_id: str, conversation_name: str, session_id: str) -> None:
        """Wipe state for a specific session."""
        ...

    # Non-abstract — shared logic available to all implementations
    def key(self, user_id: str, conversation_name: str, session_id: str) -> str:
        """Canonical key format used by all store implementations."""
        return f"{user_id}:{conversation_name}:{session_id}"
