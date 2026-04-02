from rich.prompt import Prompt
from rich import print

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import UUID
from uuid6 import uuid7  # 126

from core.security import get_password_hash
from core.logger import setup_logging, get_logger
from core.db.database_sync import get_db_ctx, init_db, Base, engine 

from models.user import User

log = get_logger(__name__)

def create_admin_user():
    name = Prompt.ask("Enter your name", default="IVMR")
    username = Prompt.ask("Enter your username", default="admin")
    email = Prompt.ask("Enter your email", default="admin@ejemplo.com")
    passwd = Prompt.ask("Enter your passwd", password=True)
    passwd_ = Prompt.ask("Confirm your passwd", password=True)
    if passwd != passwd_:
        print("[red]Passwords do not match. Please try again.[/]")
        return False
    password_hash = get_password_hash(passwd)
    init_db()  # Ensure tables are created before querying

    with get_db_ctx() as session:
        query = select(User).filter_by(email=email)
        result = session.execute(query)
        user = result.scalar_one_or_none()

    if not user is None:
        print(f"[red]User with email {email} already exists. Please try again.[/]")
        return False

    metadata = MetaData()
    user_table = Table(
        "user",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
        Column("name", String(30), nullable=False),
        Column("username", String(20), nullable=False, unique=True, index=True),
        Column("email", String(50), nullable=False, unique=True, index=True),
        Column("hashed_password", String, nullable=False),
        Column("profile_image_url", String, default="https://profileimageurl.com"),
        Column("uuid", UUID(as_uuid=True), default=uuid7, unique=True),
        Column("institution", String),
        Column("description", String),
        Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
        Column("updated_at", DateTime),
        Column("deleted_at", DateTime),
        Column("is_deleted", Boolean, default=False, index=True),
        Column("is_superuser", Boolean, default=False),
        Column("is_verified", Boolean, default=False),
        Column("tier_id", Integer, ForeignKey("tier.id"), index=True),
    )
    data = {
                "name": name,
                "email": email,
                "username": username,
                "hashed_password": password_hash,
                "is_superuser": True,
                "is_verified": True,
            }

    stmt = insert(user_table).values(data)
    with get_db_ctx() as session:
        session.execute(stmt)
        session.commit()

    log.info(f"Admin user {username} created successfully.")

    



