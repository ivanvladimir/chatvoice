import yaml
from rich.console import Console
from rich.markdown import Markdown
import sys
import os

from .parser import parse_line

from typing import Generator, Any
from core.logger import get_logger

from models import User, KB
from schemas.kb import KBUpdateInternal, KBCreate
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, insert, select
from core.db.database_sync import init_db, get_db_ctx 


log = get_logger(__name__)

class Conversation:
    def __init__(self, pathname: str, user_id: int, settings: dict):
        self.console = Console(record=True)
        self.stacks_ : list[list] = []
        self.commands : list[str] = []
        self.strategies : list[dict] = []
        self.project_pathname = str(pathname)
        self.main_file = self.load_conversation(pathname, settings)
        self.path = os.path.dirname(pathname)
        self.basename = os.path.basename(pathname)
        self.name = os.path.splitext(self.basename)[-1]
        self.user_id = user_id
 
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
        self.slots = {
        }
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
        EXIT=False
        ERROR=None
        while len(self.commands)>0 and not EXIT:
            line=self.commands.pop(0)
            chain = parse_line(line)
            STATUS = {}
            while len(chain.commands)>0 and not EXIT:
                c=chain.commands.pop(0)
                if c.name=="solve":
                    strategy_name=c.args[0]
                    if not strategy_name in self.strategies:
                        EXIT=True
                        ERROR=ValueError(f"Unknown strategy {strategy_name}")
                        break
                    self.stacks_.append(self.commands)
                    self.commands=list(self.strategies[strategy_name])
                    STATUS = {
                            'command': 'solve',
                            'ok': True
                            }
                elif c.name == "say":
                    text = str(c.args[0]).format_map(self.slots)
                    STATUS = {
                            'command': 'say',
                            'value': [text],
                            'ok': True
                            }
                    yield {"cmd":"say", "args": [text]}
    
                elif c.name == "listen":
                    variable = str(c.args[0])
                    yield {"cmd":"listen"}
                    user_input = callback()
                    self.slots[variable] = user_input or ""
                    STATUS = {
                            'command': 'listen',
                            'value': user_input or "",
                            'variable': variable,
                            'ok': True
                            }
                elif c.name == "remember":
                    if len(c.args)==1:
                        variable = str(c.args[0])
                    elif len(c.args)==0:
                        variable=STATUS['variable']
                        value=STATUS['value']
                    self.slots[variable] = value
                    with get_db_ctx() as db:
                        result = db.execute(select(KB).filter_by(user_id=self.user_id, project_path=self.project_pathname))
                        db_kb = result.scalar_one_or_none()
                        if not db_kb:
                            entry=KBCreate(user_id=self.user_id,
                                           project_path=self.project_pathname,
                                           payload={variable:value})
                            kb = KB(**entry.model_dump(mode="python"))
                            db.add(kb)
                            db.commit()
                            db.refresh(kb)

                    STATUS = {
                            'command': 'remember',
                            'value': value,
                            'variable': variable,
                            'ok': True
                            }
                else:
                    EXIT=True
                    ERROR=ValueError(f"Unknown command {c._command}")
                    break
                if not STATUS['ok']:
                    EXIT=True
                    ERROR=ValueError(f"Error while evaluating {c._command}")
                    break
 
            if len(self.commands)==0 and len(self.stacks_)>0:
                self.commands=self.stacks_.pop()

        log.info(f"Finishing execution of conversation")
        if not ERROR is None:
            raise ERROR

        
