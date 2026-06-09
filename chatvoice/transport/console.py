import asyncio
from typing import Any, Literal, Callable
from rich.prompt import Prompt
from rich.console import Console as PConsole

from models import *
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, insert, select
from core.db.database_sync import init_db, get_db_ctx 
import bcrypt

from crud.users import crud_users
from core.security import get_password_hash
from core.logger import get_logger

from sessions.manager import SessionManager
from store.memory import MemoryStateStore

log = get_logger(__name__)

class Console():
    def __init__(self, 
                 store_type: str = "memory"
                 ):
        """ Initializating the console """
        init_db()
        if store_type.startswith("memory"):
            self.store = MemoryStateStore()
            self.session_manager = SessionManager(self.store)
        self.console = PConsole()
        log.info("Starting console chat")

    def authenticate_user(self) -> dict[str, Any] | Literal[False]:
        """ Managing authentification """
        username_or_email = Prompt.ask("Enter your username or email")
        password = Prompt.ask("Enter your password", password=True)

        with get_db_ctx() as db:
            if "@" in username_or_email:
                query = select(User).filter_by(email=username_or_email, is_deleted=False, is_verified=True)
            else:
                query = select(User).filter_by(username=username_or_email, is_deleted=False, is_verified=True)
            result = db.execute(query)
            db_user = result.scalar_one_or_none()

            if not db_user:
                log.error("Username or email not found", username_or_email=username_or_email)
                return False

            if not bcrypt.checkpw(password.encode(),db_user.hashed_password.encode()):
                log.error("Authentication failed for user", username_or_email=username_or_email)
                return False
            db.expunge(db_user)
        return db_user

    def run(self, user_id: str, conversation: Callable):
        """ Run the script """
        session = self.session_manager.create(user_id, conversation)
        self.console.print(f"\n\n====== Starting conversation with {user_id} =====")
        while True:
            m = session.recv()
            if m is None:
                return
            if m["cmd"] == "say":
                self.console.print(f"{conversation.settings['name']}:",*m['args'])
            if m["cmd"] == "listen":
                input=self.console.input(f"{conversation.settings['user_name']}: ")
                session.send(input)






