import yaml
from rich.console import Console
from rich.markdown import Markdown
import sys
import os

from dataclasses import dataclass, field
from typing import Generator, Any


from core.logger import get_logger

log = get_logger(__name__)


@dataclass
class SayEvent:
    """The bot wants to say something."""
    text: str
 
 
@dataclass
class ListenEvent:
    """The bot is waiting for user input; store the reply in `variable`."""
    variable: str
    reply: str = field(default="", init=False)


class Conversation:
    def __init__(self, pathname: str):
        self.console = Console(record=True)
        self.context : dict[str, str] = {}
        self.commands : list[dict] = []
        self.main=self.load_conversation(pathname)
        self.path = os.path.dirname(pathname)
        self.basename = os.path.basename(pathname)
        self.name = os.path.splitext(self.basename)[-1]
 
    def load_conversation(self, pathname: str):
        filename = os.path.join(pathname,"main.yaml") 
        with open(filename, "r", encoding="utf-8") as stream:
            try:
                definition = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.console.print(exc)
                log.error(f"Error while reading: {filename}")
                sys.exit()

        self.commands = definition["script"]
        return filename

    def execute(self):
        for command in self.commands:
            if not isinstance(command, dict):
                raise ValueError(f"Invalid command (must be a mapping): {command!r}")
    
            if len(command) != 1:
                raise ValueError(f"Each command must have exactly one key: {command!r}")
    
            [(cmd, value)] = command.items()
    
            if cmd == "say":
                text = str(value).format_map(context)
                yield SayEvent(text=text)
    
            elif cmd == "listen":
                event = ListenEvent(variable=str(value))
                user_reply: str = yield event          # caller sends the reply back
                context[event.variable] = user_reply or ""
    
            else:
                raise ValueError(f"Unknown command: {cmd!r}")



        
