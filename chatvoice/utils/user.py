import asyncio
import csv
import re
import secrets
import string
from pathlib import Path

from rich import print
from rich.prompt import IntPrompt, Prompt
from sqlalchemy import select

from ..core.db.database_sync import get_db_ctx, init_db
from ..core.security import get_password_hash
from ..models import Tier, User
from ..schemas.user import UserCreate, UserCreateInternal, UserRole


async def _audit_admin_users_async():
    from crudadmin.admin_user.schemas import AdminUserRead

    from ..admin.initialize import create_admin_interface

    admin = create_admin_interface()

    async for admin_session in admin.db_config.get_admin_db():
        result = await admin.db_config.crud_users.get_multi(admin_session)

        # Access the actual list of users
        users = result["data"]

        print("Admin Users Audit:")
        print("-" * 50)
        for user in users:
            user = AdminUserRead(**user)
            print(f"Username: {user.username}")
            print(f"Superuser: {user.is_superuser}")
            print("-" * 30)


def audit_admin_users():
    return asyncio.run(_audit_admin_users_async())


def create_admin_user():
    """Create admin with a selectable role via CLI."""
    username = Prompt.ask("Enter your username", default="admin")
    passwd = Prompt.ask("Enter your password", password=True)
    passwd_ = Prompt.ask("Confirm your password", password=True)

    if passwd != passwd_:
        print("[red]Passwords do not match. Please try again.[/]")
        return (username, None)

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
            await admin.db_config.crud_users.create(admin_session, object=internal_data)
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
    roles = list(UserRole)
    for idx, role in enumerate(roles, 1):
        print(f"  [cyan]{idx}[/]. {role.value}")

    role_choice = IntPrompt.ask(
        "Enter your choice",
        choices=[str(i) for i in range(1, len(roles) + 1)],
        default=1,
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
            role=selected_role,
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
        role=selected_role,
    )

    new_user = User(**user_internal.model_dump())
    new_user.is_verified = True

    with get_db_ctx() as session:
        session.add(new_user)
        session.flush()
        # Capture values while session is active
        username = new_user.name
        userrole = new_user.role.value

    return username, userrole


_PASSWORD_SPECIALS = "!@#$%^&*()-_=+"


def generate_password(length: int = 8) -> str:
    """Return a random password that satisfies the ``UserCreate`` strength
    rules (>= 8 chars including a lowercase letter, an uppercase letter, a
    digit and a special character)."""
    length = max(length, 8)
    alphabet = string.ascii_letters + string.digits + _PASSWORD_SPECIALS
    chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(_PASSWORD_SPECIALS),
    ]
    chars += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def create_batch_users(prefix: str, count: int, output: Path):
    """Create ``count`` anonymous users ``<prefix>1`` .. ``<prefix><count>``.

    Every user gets name ``"Anonimo"``, email ``<username>@anonimo.com``, no
    institution or description, role ``user`` and a random strong password.
    Existing usernames/emails are left untouched. Each created username and
    its plaintext password are written to ``output`` as CSV so they can be
    distributed.

    Returns ``(created_count, skipped_count, output_path)``.

    Raises
    ------
    ValueError
        If the prefix is empty/invalid, the count is < 1, or the resulting
        usernames would exceed the 20-character limit.
    """
    prefix = prefix.strip()
    if not re.fullmatch(r"[a-z0-9]+", prefix):
        raise ValueError(
            "Prefix must be non-empty and contain only lowercase letters and digits."
        )
    if count < 1:
        raise ValueError("Count must be >= 1.")

    longest_username = len(prefix) + len(str(count))
    if longest_username > 20:
        raise ValueError(
            f"Username '{prefix}{count}' would exceed the 20-character limit; "
            "use a shorter prefix or a smaller count."
        )

    init_db()

    created: list[tuple[str, str, str]] = []
    skipped: list[str] = []

    with get_db_ctx() as session:
        for n in range(1, count + 1):
            username = f"{prefix}{n}"
            email = f"{username}@anonimo.com"

            existing = session.execute(
                select(User).filter((User.username == username) | (User.email == email))
            ).scalar_one_or_none()
            if existing is not None:
                skipped.append(username)
                continue

            password = generate_password()

            # Validate through the same schema the interactive command uses.
            user_create = UserCreate(
                name="Anonimo",
                username=username,
                email=email,
                institution=None,
                description=None,
                password=password,
                role=UserRole.user,
            )
            user_internal = UserCreateInternal(
                name=user_create.name,
                username=user_create.username,
                email=user_create.email,
                institution=None,
                description=None,
                hashed_password=get_password_hash(password),
                role=UserRole.user,
            )
            new_user = User(**user_internal.model_dump())
            new_user.is_verified = True

            session.add(new_user)
            created.append((username, email, password))

    output = Path(output)
    if output.parent and not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["username", "email", "name", "password"])
        for username, email, password in created:
            writer.writerow([username, email, "Anonimo", password])

    return len(created), len(skipped), output


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

    print(f"Tiername '{tiername}' created successfully.")
