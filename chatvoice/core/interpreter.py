from typing import Generator, Any
from pathlib import Path

from ..store.sql_store import SqlAlchemyMemoryStore
from .logger import get_logger
from .parser import parse_line, Command
from .expresion_evaluator import ExpressionEvaluator
from .conversation import Conversation

from .commands import (
    cmd_say,
    cmd_listen,
    cmd_solve,
    cmd_return,
    cmd_llm,
    cmd_set,
    cmd_exec,
    cmd_tag,
    cmd_remember,
    cmd_info,
    ExecutionState,
)

log = get_logger(__name__)


class InterpreterStop(Exception):
    """Raised to immediately halt the interpreter."""

    def __init__(self, reason: Exception):
        self.reason = reason


class CommandError(Exception):
    """Raised when a specific command fails."""

    pass


class Interpreter:
    """Runs the execution of commands within a parsed chain."""

    def __init__(
        self,
        project_pathname: Path,
        user_id: int,
        settings: dict = None,
        slots: dict = None,
        llm_client=None,
    ):
        self.project_pathname = project_pathname

        # Path.stem correctly gets the filename without the extension
        self.name = project_pathname.stem

        self.stack_ = []
        self.exit = False
        self.error = None
        self.status: dict = {}
        self.llm_client = llm_client

        self.conversation = Conversation(
            project_pathname, user_id, settings=settings or {}, slots=slots or {}
        )
        self.settings: dict = self.conversation.settings
        self.commands = list(self.conversation.commands)
        self.state = ExecutionState(
            conversation=self.conversation, commands=self.commands
        )
        self.evaluator = ExpressionEvaluator(
            restricted_locals=self.conversation._restricted_locals,
            initial_slots=self.conversation.slots,
        )
        self.memory_store = SqlAlchemyMemoryStore()

        self.ctx = {
            "conversations": self.conversation.conversations,
            "templates": self.conversation.templates,
            "prompts": self.conversation.prompts,
            "llm_client": self.llm_client,
            "memory_store": self.memory_store,
            "state": self.state,
            "project_name": self.name,  # <-- ADD THIS
        }

        self.command_registry = {
            "say": cmd_say,
            "listen": cmd_listen,
            "set": cmd_set,
            "solve": cmd_solve,
            "tag": cmd_tag,
            "return": cmd_return,
            "llm": cmd_llm,
            "exec": cmd_exec,
            "remember": cmd_remember,
            "info": cmd_info,
        }

    def run(self, callback, state: dict = None) -> Generator[dict, Any, None]:
        log.info(f"Starting execution of conversation {self.name}")

        if state:
            self.conversation.slots.update(state.get("slots", {}))

        self.status = {}

        try:
            while self.state.commands and not self.exit:
                line = self.state.commands.pop(0)
                chain = parse_line(line)
                yield from self._run_chain(chain, callback)

                # When commands run out, check the stack we mutated in cmd_solve
                if not self.state.commands and self.state.stack:
                    obj = self.state.stack.pop()
                    if len(obj) == 1:  # Strategy
                        self.state.commands = obj[0]
                        log.info("Resuming after strategy")
                    elif len(obj) == 2:  # Conversation
                        old_conversation, commands = obj
                        old_conversation.slots.update(self.state.conversation.return_)
                        self.state.conversation, self.state.commands = (
                            old_conversation,
                            commands,
                        )
                        log.info("Resuming execution of parent conversation")
                        # IMPORTANT: Tell the evaluator to update its context with the returned slots!
                        self.evaluator.update_slots(self.state.conversation.slots)

        except CommandError as e:
            log.error(f"Execution halted: {e}")
            raise

        yield from ()
        log.info(f"Finishing execution of conversation {self.name}")

    def _run_chain(self, chain, callback) -> Generator[dict, Any, None]:
        """Execute each command in the given chain sequentially."""
        is_continuation = False

        while chain.commands and not self.exit:
            c = chain.commands.pop(0)
            # Handle shorthand dot-commands (e.g., .my_func -> exec my_func)
            if c.name.startswith("."):
                c = Command(
                    name="exec",
                    _command=c._command,
                    args=[c.name[1:]] + list(c.args),
                    condition=c.condition,
                )

            if c.condition is not None and not self.evaluator.evaluate_condition(
                c.condition
            ):
                yield from ()
                continue

            handler = self.command_registry.get(c.name)
            if handler:
                cmd_ctx = {
                    **self.ctx,  # Base context(templates, state, etc.)
                    "is_continuation": is_continuation,
                    "prev_status": self.status,
                    "memory_store": self.memory_store,
                }
            else:
                raise InterpreterStop(ValueError(f"Unknown command: {c.name}"))

            # Pass a lightweight context dict instead of `self`
            self.status = yield from handler(c.args, cmd_ctx, self.evaluator, callback)

            is_continuation = True
        yield from ()
