import asyncio
from typing import Any, Literal
from rich.prompt import Prompt

from models import *
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, insert, select
from core.db.database_sync import init_db, get_db_ctx 
import bcrypt

from crud.users import crud_users
from core.security import get_password_hash

from core.logger import get_logger

log = get_logger(__name__)

class Console():
    def __init__(self, 
                 name: str = "chatvoice",
                 ):
        init_db()

    def authenticate_user(self) -> dict[str, Any] | Literal[False]:
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

        return db_user

    def run(user_id: str, conversation: Callable):
        store = MemoryStateStore()





