from typing import Any, Literal, Callable
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.console import Console as PConsole

from models import User
from schemas.user import UserRead
from sqlalchemy import select
from core.db.database_sync import init_db, get_db_ctx 
import bcrypt

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
        self.console = PConsole(record=True)
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
            user_read = UserRead.model_validate(db_user)
            db.expunge(db_user)
        return user_read

    def run(self, user_id: int, interpreter: Callable):
        """ Run the script """
        session = self.session_manager.create(user_id, interpreter)
        self.console.print(f"\n\n====== Starting conversation with {user_id} =====")
        while True:
            m = session.recv()
            if m is None:
                return
            if m["cmd"] == "say" and len(m['args']) > 0:
                for msg in m['args']:
                    self.console.print(f"[blue]{interpreter.settings['_name_system']}[/]:",end=" ")
                    self.console.print(Markdown(msg))
            elif m["cmd"] == "listen":
                input=self.console.input(f"[red]{interpreter.settings['_name_user']}[/]: ")
                session.send(input)
                self.console.print()
            elif m["cmd"] == "info" and len(m['args']) > 0:
                self.console.print("[yellow]INFO: [/]")
                for label,info in m['args']:
                    self.console.print(f"[cyan]  {label: <10}: {info}[/]")
