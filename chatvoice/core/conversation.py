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

log = get_logger(__name__)

class Conversation:
    def __init__(self, project_pathname: str, user_id: int, filename: str = "main.yaml", settings: dict = {}, slots: dict = {}):
        self.project_pathname = project_pathname
        self.console = Console(record=True)
        self.stacks_ : list[list] = []
        self.commands : list[str] = []
        self.strategies : list[dict] = []
        self.conversations : dict = {}
        self.slots : dict = {}
        self.return_ : dict = {}
        self.user_id = user_id
        self._load_conversation(project_pathname, filename, settings, slots)
 
    def _load_conversation(self, project_pathname: str, filename: str = "main.yaml", settings_: dict = {}, slots_ : dict = {}):
        log.info(f"Starting loading conversation from: {project_pathname}")
        filename = os.path.join(project_pathname,filename) 
        with open(filename, "r", encoding="utf-8") as stream:
            try:
                definition = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.console.print(exc)
                log.error(f"Error while reading: {filename}")
                sys.exit()


        slots = definition.get("slots",{})
        slots.update(slots_)
        self.load_slots(slots, filename.endswith('main.yaml'))

        
        settings= definition.get("settings",{})
        settings.update(settings_)
        self.load_settings(settings)
        
        self.commands = list(definition.get("script",{}))
        self.load_strategies(definition.get("strategies",{}))
        self.load_conversations(definition.get("conversations",{}),settings=self.settings)
        
        log.info(f"Finishing loading conversation from: {filename}")

    def load_slots(self, slots_: dict, main: bool = True):
        if main:
            with get_db_ctx() as db:
                result = db.execute(
                    select(KB).filter_by(
                        user_id=self.user_id,
                        project_path=str(self.project_pathname),
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

    def load_conversations(self, conversations_: dict, settings: dict = {} ):
        self.conversations = {
        }
        for filename in conversations_:
            basename = os.path.splitext(os.path.basename(filename))[0]
            if not basename in self.conversations: 
                log.info(f"Loading conversation '{filename}'")
                self.conversations[basename]={'project_pathname':self.project_pathname,
                                              'filename':filename,
                                              'user_id':self.user_id}
            else:
                log.info(f"Conversation '{filename}' already in {self.basename}, it will be ignored")

    def load_settings(self, settings_: dict):
        self.settings = {
            "_name_user":"USER",
            "_name_system":"SYSTEM"
        }
        self.settings.update(settings_)


