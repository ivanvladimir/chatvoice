import yaml
from rich.console import Console
from rich.markdown import Markdown
import sys
import os

from typing import Generator, Any
from core.logger import get_logger

log = get_logger(__name__)

class Conversation:
    def __init__(self, pathname: str, settings: dict):
        self.console = Console(record=True)
        self.commands : list[dict] = []
        self.main_file = self.load_conversation(pathname, settings)
        self.path = os.path.dirname(pathname)
        self.basename = os.path.basename(pathname)
        self.name = os.path.splitext(self.basename)[-1]
 
    def load_conversation(self, pathname: str, settings_: dict):
        log.info(f"Starting loading conversation from: {pathname}")
        filename = os.path.join(pathname,"main.yaml") 
        with open(filename, "r", encoding="utf-8") as stream:
            try:
                definition = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.console.print(exc)
                log.error(f"Error while reading: {filename}")
                sys.exit()

        self.commands = definition.get("script",{})
        self.load_slots(definition.get("slots",{}))
        settings= definition.get("settings",{})
        settings.update(settings_)
        self.load_settings(settings)
        log.info(f"Finishing loading conversation from: {filename}")
        return filename

    def load_slots(self, slots_: dict):
        self.slots = {
        }
        self.slots.update(slots_)

    def load_settings(self, settings_: dict):
        self.settings = {
            "user_name":"USER",
            "name":"SYSTEM"
        }
        self.settings.update(settings_)

    def execute(self, callback, state: dict):
        log.info(f"Starting execution of conversation")
        self.slots.update(state.get('slots',{}))
        for command in self.commands:
            if not isinstance(command, dict):
                raise ValueError(f"Invalid command (must be a mapping): {command!r}")
    
            if len(command) != 1:
                raise ValueError(f"Each command must have exactly one key: {command!r}")
    
            [(cmd, value)] = command.items()
    
            if cmd == "say":
                text = str(value).format_map(self.slots)
                yield {"cmd":"say", "args": [text]}
    
            elif cmd == "listen":
                variable = str(value)
                yield {"cmd":"listen"}
                user_input = callback()
                self.slots[variable] = user_input or ""
            else:
                raise ValueError(f"Unknown command: {cmd!r}")



        
