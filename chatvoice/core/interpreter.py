from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from ..store.conversation_store import ConversationLogStore
from ..store.sql_store import SqlAlchemyMemoryStore
from .commands import (
    CommandError,  # Import from commands to avoid duplication
    ExecutionState,
    cmd_exec,
    cmd_info,
    cmd_listen,
    cmd_llm,
    cmd_llm_extract,
    cmd_remember,
    cmd_return,
    cmd_say,
    cmd_set,
    cmd_sleep,
    cmd_solve,
    cmd_tag,
)
from .conversation import Conversation
from .expresion_evaluator import ExpressionEvaluator
from .logger import get_logger
from .parser import Command, parse_line, parse_structured_command

log = get_logger(__name__)

# Safety cap on `while <condition> then <command>` guards: if the condition
# never turns false (a script bug, e.g. forgetting to update the tested
# slot), this stops the loop instead of hanging the session thread forever.
MAX_WHILE_ITERATIONS = 1000


class InterpreterStop(Exception):
    """Raised to immediately halt the interpreter."""

    def __init__(self, reason: Exception):
        self.reason = reason


class Interpreter:
    """
    Runs the execution of commands within a parsed chain.
    Manages the execution stack for strategies and sub-conversations.
    """

    def __init__(
        self,
        project_pathname: Union[str, Path],
        user_id: int,
        settings: Optional[Dict[str, Any]] = None,
        slots: Optional[Dict[str, Any]] = None,
        llm_client: Any = None,
        memory_store: Optional[Any] = None,  # Injected for testability
        conversation_log_id: Optional[int] = None,
        conversation_store: Optional[Any] = None,  # Injected for testability
    ):
        """
        Initialize the Interpreter and the root Conversation.

        Args:
            project_pathname: The base directory path for the project.
            user_id: The ID of the user executing the conversation.
            settings: Optional settings to override YAML definitions.
            slots: Optional initial slots to inject.
            llm_client: The client used to communicate with the LLM.
            memory_store: Optional memory store instance. Defaults to SqlAlchemyMemoryStore.
            conversation_log_id: DB id of the ConversationLog row for this run, if
                any (see chatvoice.models.conversation). When set, cmd_say/cmd_listen
                persist each turn via conversation_store as it happens.
            conversation_store: Optional store instance. Defaults to ConversationLogStore.
        """
        # Ensure project_pathname is a string for os.path operations in Conversation
        self.project_pathname = str(project_pathname)

        # Safely extract the project folder name
        self.name = Path(self.project_pathname).name

        self.exit = False
        self.error: Optional[Exception] = None
        self.status: Dict[str, Any] = {}
        self.llm_client = llm_client

        # Per-session conversation history: {"role": "user"|"assistant", "text": str}
        # entries appended by cmd_say/cmd_listen. Kept as a single list instance
        # (mutated in place, never reassigned) so the reference shared into
        # self.ctx below and restored from persisted state in run() stays valid.
        self.history: List[Dict[str, str]] = []

        # Initialize Conversation (convert path back to string to satisfy Conversation type hints)
        self.conversation = Conversation(
            self.project_pathname, user_id, settings=settings or {}, slots=slots or {}
        )

        self.settings: Dict[str, Any] = self.conversation.settings
        self.commands: List[Union[str, dict]] = list(self.conversation.commands)

        self.state = ExecutionState(
            conversation=self.conversation, commands=self.commands
        )

        self.evaluator = ExpressionEvaluator(
            restricted_locals=self.conversation._restricted_locals,
            initial_slots=self.conversation.slots,
        )

        # Use injected store or fallback to default
        self.memory_store = memory_store or SqlAlchemyMemoryStore()
        self.conversation_log_id = conversation_log_id
        self.conversation_store = conversation_store or ConversationLogStore()

        # Base context passed to all commands
        self.ctx: Dict[str, Any] = {
            "conversations": self.conversation.conversations,
            "templates": self.conversation.templates,
            "prompts": self.conversation.prompts,
            "llm_client": self.llm_client,
            "memory_store": self.memory_store,
            "state": self.state,
            "project_name": self.name,
            "history": self.history,
            "conversation_log_id": self.conversation_log_id,
            "conversation_store": self.conversation_store,
        }

        self.command_registry = {
            "say": cmd_say,
            "listen": cmd_listen,
            "set": cmd_set,
            "solve": cmd_solve,
            "tag": cmd_tag,
            "return": cmd_return,
            "llm": cmd_llm,
            "llm_extract": cmd_llm_extract,
            "exec": cmd_exec,
            "remember": cmd_remember,
            "info": cmd_info,
            "sleep": cmd_sleep,
        }

    def run(
        self, callback: callable, state: Optional[Dict[str, Any]] = None
    ) -> Generator[Dict[str, Any], Any, None]:
        """
        Main execution loop. Pops commands, parses them into chains,
        and handles sub-conversation/strategy stack unwinding.

        Args:
            callback: Function called by commands like 'listen' to get user input.
            state: Optional state dictionary to inject into slots before starting.

        Yields:
            Dictionaries of UI-bound data (e.g., text to say, tags to set).

        Raises:
            CommandError: If a command explicitly fails and halts execution.
        """
        log.info(f"Starting execution of conversation {self.name}")

        if state:
            self.conversation.slots.update(state.get("slots", {}))
            # In-place: preserves the list object shared into self.ctx["history"].
            self.history[:] = state.get("history", [])

        self.status = {}

        try:
            while self.state.commands and not self.exit:
                line = self.state.commands.pop(0)
                chain = (
                    parse_structured_command(line)
                    if isinstance(line, dict)
                    else parse_line(line)
                )

                # Execute the parsed chain (e.g., "say hello | set var 1")
                yield from self._run_chain(chain, callback)

                # Stack Unwinding: If commands run out, check if we returning from a jump
                if not self.state.commands and self.state.stack:
                    obj = self.state.stack.pop()

                    if len(obj) == 1:  # Returning from a Strategy
                        self.state.commands = obj[0]
                        log.info("Resuming after strategy")

                    elif len(obj) == 2:  # Returning from a Sub-conversation
                        old_conversation, commands = obj
                        # Map returned variables back into the parent conversation's slots
                        old_conversation.slots.update(self.state.conversation.return_)

                        self.state.conversation = old_conversation
                        self.state.commands = commands

                        log.info("Resuming execution of parent conversation")
                        # CRITICAL: Sync the evaluator with the parent conversation's updated slots
                        self.evaluator.update_slots(self.state.conversation.slots)

        except CommandError as e:
            log.error(f"Execution halted due to CommandError: {e}")
            raise

        yield from ()  # Maintain generator protocol at the end of execution
        log.info(f"Finishing execution of conversation {self.name}")

    def _run_chain(
        self, chain: Any, callback: callable
    ) -> Generator[Dict[str, Any], Any, None]:
        """
        Execute each command in a parsed chain sequentially.
        Handles conditional execution, dot-shorthand expansion, and continuation piping.

        Args:
            chain: A parsed chain object containing a list of Command objects.
            callback: Function called by commands like 'listen' to get user input.

        Yields:
            Dictionaries of UI-bound data from the executed commands.

        Raises:
            InterpreterStop: If an unknown command is encountered.
        """
        is_continuation = False

        while chain.commands and not self.exit:
            c: Command = chain.commands.pop(0)

            # Handle shorthand dot-commands (e.g., .my_func -> exec my_func)
            if c.name.startswith("."):
                c = Command(
                    name="exec",
                    _command=c._command,
                    args=[c.name[1:]] + list(c.args),
                    condition=c.condition,
                    condition_type=c.condition_type,
                )

            if c.condition_type == "while":
                # Re-check the condition and re-run the guarded command until
                # it's false, e.g. `while attempts < 3 then listen entrada`.
                # condition is always set alongside condition_type by the parser.
                assert c.condition is not None
                ran_once = False
                iterations = 0
                while not self.exit and self.evaluator.evaluate_condition(c.condition):
                    iterations += 1
                    if iterations > MAX_WHILE_ITERATIONS:
                        log.warning(
                            f"while guard on '{c.name}' exceeded "
                            f"{MAX_WHILE_ITERATIONS} iterations (condition: "
                            f"{c.condition}); stopping to avoid an infinite loop."
                        )
                        break

                    self.status = yield from self._dispatch(
                        c, is_continuation, callback
                    )
                    ran_once = True

                if ran_once:
                    is_continuation = True
                continue

            # Evaluate conditional execution (e.g., `if slot == true then say hello`)
            if c.condition is not None and not self.evaluator.evaluate_condition(
                c.condition
            ):
                yield from ()
                continue

            self.status = yield from self._dispatch(c, is_continuation, callback)

            # The next command in the chain will pipe this command's output as an argument
            is_continuation = True

        yield from ()  # Maintain generator protocol

    def _dispatch(
        self, c: Command, is_continuation: bool, callback: callable
    ) -> Generator[Dict[str, Any], Any, Dict[str, Any]]:
        """Look up and run a single command's handler, returning its status dict."""
        handler = self.command_registry.get(c.name)

        if not handler:
            raise InterpreterStop(ValueError(f"Unknown command: {c.name}"))

        # Build the specific context payload for this exact command execution
        cmd_ctx = {
            **self.ctx,  # Base context (templates, state, etc.)
            "is_continuation": is_continuation,
            "prev_status": self.status,
            "memory_store": self.memory_store,
        }

        return (yield from handler(c.args, cmd_ctx, self.evaluator, callback))
