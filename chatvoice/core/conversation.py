import yaml
from rich.console import Console
from rich.markdown import Markdown
import sys
import os
from datetime import datetime, UTC

from typing import Generator, Any
from core.logger import get_logger

from models import User, KB
from schemas.kb import KBUpdateInternal, KBCreate
from sqlalchemy import update, insert, Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, insert, select
from core.db.database_sync import init_db, get_db_ctx 

from .parser import parse_line
from .interpreter import Interpreter

log = get_logger(__name__)

class Conversation:
    def __init__(self, pathname: str, user_id: int, settings: dict):
        self.console = Console(record=True)
        self.stacks_ : list[list] = []
        self.commands : list[str] = []
        self.strategies : list[dict] = []
        self.project_pathname = str(pathname)
        self.path = os.path.dirname(pathname)
        self.basename = os.path.basename(pathname)
        self.name = os.path.splitext(self.basename)[-1]
        self.user_id = user_id
        self.main_file = self.load_conversation(pathname, settings)
 
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

        self.commands = list(definition.get("script",{}))
        self.load_slots(definition.get("slots",{}))
        self.load_strategies(definition.get("strategies",{}))
        settings= definition.get("settings",{})
        settings.update(settings_)
        self.load_settings(settings)
        log.info(f"Finishing loading conversation from: {filename}")
        return filename

    def load_slots(self, slots_: dict):
        with get_db_ctx() as db:
            result = db.execute(
                select(KB).filter_by(
                    user_id=self.user_id,
                    project_path=self.project_pathname,
                )
            )
            kb = result.scalar_one_or_none()
            if kb:
                self.slots = dict(kb.payload)
            else:
                self.slots = dict()
        self.slots.update(slots_)

    def load_strategies(self, strategies_: dict):
        self.strategies = {
        }
        self.strategies.update(strategies_)

    def load_settings(self, settings_: dict):
        self.settings = {
            "_name_user":"USER",
            "_name_system":"SYSTEM"
        }
        self.settings.update(settings_)

    def execute(self, callback, state: dict):
        log.info(f"Starting execution of conversation")
        self.slots.update(state.get('slots',{}))
    
        interpreter = Interpreter(self)
        while len(self.commands) > 0 and not interpreter.exit:
            line = self.commands.pop(0)
            chain = parse_line(line)
            yield from interpreter.run_chain(chain, callback)
            if len(self.commands) == 0 and len(self.stacks_) > 0:
                self.commands = self.stacks_.pop()

        log.info(f"Finishing execution of conversation")
        if interpreter.error is not None:
            raise interpreter.error
        
