from ..store.base import BaseStateStore


class MemoryStateStore(BaseStateStore):
    def __init__(self):
        self._store: dict[str, dict] = {}

    def get(self, user_id: str, conversation_name: str, session_id: str) -> dict:
        return self._store.get(self.key(user_id, conversation_name, session_id), {})

    def set(
        self, user_id: str, state: dict, conversation_name: str, session_id: str
    ) -> None:
        self._store[self.key(user_id, conversation_name, session_id)] = state

    def delete(self, user_id: str, conversation_name: str, session_id: str) -> None:
        self._store.pop(self.key(user_id, conversation_name, session_id), None)
