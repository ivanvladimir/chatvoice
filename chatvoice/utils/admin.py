from rich.prompt import Prompt
from rich import print


from sqlalchemy import select

from core.security import get_password_hash
from core.logger import get_logger
from core.db.database_sync import get_db_ctx, init_db 

from models import User, Tier

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
    hashed_password = get_password_hash(passwd)
    init_db()  # Ensure tables are created before querying

    with get_db_ctx() as session:
        query = select(User).filter_by(email=email)
        result = session.execute(query)
        user = result.scalar_one_or_none()

    if user is not None:
        print(f"[red]User with email '{email}' already exists. Please try again.[/]")
        return False

    admin = User(name=name, email=email, username=username, hashed_password=hashed_password, is_verified=True, is_superuser=True)
    with get_db_ctx() as session:
        session.add(admin)
        session.flush()

    log.info(f"Admin user '{username}' created successfully.")

    
def create_tier():
    tiername = Prompt.ask("Enter the tier name", default="free")
    init_db()  # Ensure tables are created before querying

    with get_db_ctx() as session:
        query = select(Tier).where(Tier.name == tiername)
        result = session.execute(query)
        tier = result.scalar_one_or_none()

    if tier is not None:
        print(f"[red]Tier name '{tiername}' already exists[/]")
        return False

    with get_db_ctx() as session:
        session.add(Tier(name=tiername))
        session.commit()

    log.info(f"Tiername '{tiername}' created successfully.")




