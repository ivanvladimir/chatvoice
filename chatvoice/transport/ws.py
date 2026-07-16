from typing import Any, Literal, Callable
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.console import Console as PConsole

from sqlalchemy import select
import bcrypt

from ..core.logger import get_logger
from ..core.db.database_sync import init_db, get_db_ctx 
from ..models import User
from ..schemas.user import UserRead

from ..sessions.manager import SessionManager
from ..store.memory import MemoryStateStore


log = get_logger(__name__)

class WS():
    def __init__(self, 
                 store_type: str = "memory"
                 ):
        """ Initializating the ws """
        init_db()
        if store_type.startswith("memory"):
            self.store = MemoryStateStore()
            self.session_manager = SessionManager(self.store)
        log.info("Starting ws chat")

    def create_session(self, user_id: int, interpreter: Callable):
        """ Run the script """
        session = self.session_manager.create(user_id, interpreter)
        return session

    def validate(self,ws_sesssion: str = None):
        if ws_sesssion == None:
            return 
        session= self.session_manager.get(ws_sesssion)
        if session:
            return session.user_id

    def get_session(self,ws_sesssion: str = None):
        if ws_sesssion == None:
            return 
        return self.session_manager.get(ws_sesssion)

