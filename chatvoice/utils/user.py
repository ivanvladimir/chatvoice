from sqlalchemy import select

from enum import Enum

from rich.prompt import Prompt, IntPrompt
from rich import print

from ..models import User
from ..schemas.user import UserRole, UserCreate, UserCreateInternal
from ..core.security import get_password_hash
from ..core.db.database_sync import get_db_ctx, init_db

import asyncio

def create_admin_user():
    """Create admin with a selectable role via CLI."""
    username = Prompt.ask("Enter your username", default="admin")
    passwd = Prompt.ask("Enter your password", password=True)
    passwd_ = Prompt.ask("Confirm your password", password=True)
    
    if passwd != passwd_:
        print("[red]Passwords do not match. Please try again.[/]")
        return (name, None)

    return asyncio.run(_create_admin_user_async(username, passwd))


async def _create_admin_user_async(username: str, password: str):
    """Internal async function to handle database operations."""
    from crudadmin.admin_user.schemas import AdminUserCreateInternal
    from ..admin.initialize import create_admin_interface

    admin = create_admin_interface()
    
    async for admin_session in admin.db_config.get_admin_db():
        try:
            hashed_password = admin.admin_user_service.get_password_hash(password)
            internal_data = AdminUserCreateInternal(
                username=username,
                hashed_password=hashed_password,
            )

            await admin.initialize()
            await admin.db_config.crud_users.create(
                admin_session, object=internal_data
            )
            await admin_session.commit()
            return username, True

        except Exception as e:
            print(f"[red]Error creating admin {username}: {e}.[/]")
            await admin_session.rollback()
        return username, False


def create_user():
    """Create a user with a selectable role via CLI."""
    name = Prompt.ask("Enter your name", default="IVMR")
    username = Prompt.ask("Enter your username", default="user")
    email = Prompt.ask("Enter your email", default="user@ejemplo.com")
    institution = Prompt.ask("Enter the name of your institution", default="")
    description = Prompt.ask("Enter a brief description of yourself", default="")
    
    # Role selection
    print("\n[bold]Select user role:[/]")
    roles=list(UserRole)
    for idx, role in enumerate(roles, 1):
        print(f"  [cyan]{idx}[/]. {role.value}")
   
    role_choice = IntPrompt.ask(
        "Enter your choice",
        choices=[str(i) for i in range(1, len(roles) + 1)],
        default=1
    )
    selected_role = roles[role_choice - 1]
    
    passwd = Prompt.ask("Enter your password", password=True)
    passwd_ = Prompt.ask("Confirm your password", password=True)
    
    if passwd != passwd_:
        print("[red]Passwords do not match. Please try again.[/]")
        return (name, None)
    
    # Validate with Pydantic schema
    try:
        user_create = UserCreate(
            name=name,
            username=username,
            email=email,
            institution=institution or None,
            description=description or None,
            password=passwd,
            role=selected_role
        )
    except Exception as e:
        print(f"[red]Validation error: {e}[/]")
        return (name, None)
    
    hashed_password = get_password_hash(passwd)
    init_db()

    with get_db_ctx() as session:
        query = select(User).filter_by(email=email)
        result = session.execute(query)
        user = result.scalar_one_or_none()

    if user is not None:
        print(f"[red]User with email '{email}' already exists. Please try again.[/]")
        return (name, None)

    # Use UserCreateInternal with selected role
    user_internal = UserCreateInternal(
        name=user_create.name,
        username=user_create.username,
        email=user_create.email,
        institution=user_create.institution,
        description=user_create.description,
        hashed_password=hashed_password,
        role=selected_role
    )
    
    new_user = User(**user_internal.model_dump())
    new_user.is_verified = True
   
    with get_db_ctx() as session:
        session.add(new_user)
        session.flush()
        # Capture values while session is active
        user_name = new_user.name
        user_role = new_user.role.value

    return name, user_role
    
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
