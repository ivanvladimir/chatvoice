import queue
import threading
from typing import Optional

from ..core.interpreter import Interpreter, InterpreterStop
from ..core.logger import get_logger
from ..store.base import BaseStateStore

log = get_logger(__name__)

# Sentinel to unblock the queue when stopping
_STOP_SENTINEL = object()


class ChatSession:
    def __init__(
        self,
        user_id: str,
        session_id: str,
        interpreter: "Interpreter",
        store: "BaseStateStore",
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.interpreter_name = interpreter.name
        self.interpreter = interpreter
        self.store = store

        self._inbox: queue.Queue = queue.Queue()
        self._outbox: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(self.interpreter,),
            daemon=True,
            name=f"session-{self.user_id}-{self.session_id[:8]}",
        )
        self._thread.start()

    def stop(self):
        """Signal the interpreter thread to stop."""
        self._stop_event.set()
        # Unblock _recv_from_user if it's waiting
        try:
            self._inbox.put_nowait(_STOP_SENTINEL)
        except queue.Full:
            pass

    def wait(self, timeout: float = 2.0) -> bool:
        """Wait for the thread to finish. Returns True if finished."""
        if self._thread:
            self._thread.join(timeout=timeout)
            return not self._thread.is_alive()
        return True

    # --- Public API (called from WebSocket handler) ---

    def send(self, message: str):
        self._inbox.put(message)

    def recv(self) -> Optional[dict]:
        return self._outbox.get()

    # --- Private API (called from script thread) ---

    def _send_to_user(self, message: dict):
        if not self._stop_event.is_set():
            self._outbox.put(message)

    def _recv_from_user(self) -> str:
        """Blocks until user replies or stop is signaled."""
        while not self._stop_event.is_set():
            try:
                msg = self._inbox.get(timeout=0.5)
                if msg is _STOP_SENTINEL:
                    raise InterpreterStop(Exception("Session stopped"))
                return msg
            except queue.Empty:
                continue
        raise InterpreterStop(Exception("Session stopped"))

    def _run(self, interpreter: "Interpreter"):
        state = self.store.get(self.user_id, self.interpreter_name, self.session_id)

        try:
            gen = interpreter.run(self._recv_from_user, state)
            for message in gen:
                if self._stop_event.is_set():
                    break
                self._send_to_user(message)

        except InterpreterStop:
            log.info(f"Session {self.session_id} stopped")
        except Exception as e:
            log.exception(f"Error in session {self.session_id}")
            self._send_to_user({"cmd": "error", "args": [str(e)]})
        finally:
            # Persist final state
            final_state = {"slots": dict(interpreter.conversation.slots)}
            self.store.set(
                self.user_id, self.interpreter_name, self.session_id, final_state
            )
            # Signal to WebSocket handler that we're done
            self._outbox.put(None)
