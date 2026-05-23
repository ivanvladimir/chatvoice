import queue
from store.base import BaseStateStore
from typing import Callable
import threading

def global_thread_exception_hook(args):
    print(f"Thread {args.thread.name} crashed: {args.exc_value}")

threading.excepthook = global_thread_exception_hook

class ChatSession:
    def __init__(self, user_id: str, session_id: str, conversation: Callable, store: BaseStateStore):
        self.user_id = user_id
        self.session_id = session_id
        self.conversation_name=conversation.name
        self.store = store

        # Two queues act as the communication bridge between
        # the async WebSocket handler and the blocking script thread.
        # inbox  = user messages  → script
        # outbox = bot responses  → WebSocket handler
        self._inbox: queue.Queue = queue.Queue()
        self._outbox: queue.Queue = queue.Queue()

        # daemon=True means the thread dies automatically when the
        # main process exits — no manual cleanup needed on shutdown.
        self._thread = threading.Thread(
            target=self._run, args=(conversation,), daemon=True, name=f"session-{user_id}-{session_id}"
        )

    def start(self):
        # Called by SessionManager after creating the session.
        # Starts the script thread — from this point the script
        # runs independently and blocks on _inbox when waiting for input.
        self._thread.start()

    # --- Public API (called from the WebSocket handler) ---

    def send(self, message: str):
        # WebSocket handler → script thread.
        # Non-blocking: just drops the message into the queue and returns.
        self._inbox.put(message)

    def recv(self) -> str:
        # WebSocket handler ← script thread.
        # BLOCKS until the script yields a response.
        # In the async handler this is wrapped with asyncio.to_thread()
        # so it doesn't freeze the event loop.
        return self._outbox.get()

    # --- Private API (called from inside the script thread) ---

    def _send_to_user(self, message: str):
        # Script → outbox. The WebSocket handler picks it up via recv().
        self._outbox.put(message)

    def _recv_from_user(self) -> str:
        # Script ← inbox. BLOCKS the script thread until the user replies.
        # This is the callable passed into the script as recv().
        return self._inbox.get()

    def _run(self, conversation: Callable):
        # Runs entirely inside the script thread.

        # Load whatever state was saved from a previous session.
        state = self.store.get(self.user_id, self.conversation_name, self.session_id)

        # Build the generator, passing in the two interaction primitives.
        # The script never touches queues or threads directly —
        # it only calls recv() and yields strings.
        gen = conversation.execute(self._recv_from_user,state)

        # Each yield from the script is a bot message.
        # We forward it to the outbox so the WebSocket handler can send it.
        for message in gen:
            self._send_to_user(message)

        # Script is exhausted — persist final state.
        self.store.set(self.user_id, self.conversation_name, self.session_id, state)

        # Sentinel value: tells the WebSocket handler the conversation
        # is over so it can close the connection cleanly.
        self._outbox.put(None)
