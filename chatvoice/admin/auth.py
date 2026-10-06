from sqlalchemy import or_, select
from starlette.requests import Request
from starlette_admin.auth import AdminUser, AuthProvider, LoginFailed

from ..core.db.database import local_session
from ..core.security import verify_password
from ..core.types import UserRole
from ..models.user import User

SESSION_KEY = "admin_user_id"


async def _find_admin(*criteria) -> User | None:
    """The active, verified app user with role=admin matching `criteria`, or None."""
    async with local_session() as db:
        result = await db.execute(
            select(User).where(
                *criteria,
                User.role == UserRole.admin,
                User.is_deleted.is_(False),
                User.is_verified.is_(True),
            )
        )
        return result.scalar_one_or_none()


class AdminAuthProvider(AuthProvider):
    """
    Admin login against the app's own users: only those with role=admin.

    The session stores just the user id; every request re-checks that the user
    is still an active admin, so demoting or deleting a user locks them out
    immediately.
    """

    async def login(
        self, username: str, password: str, remember_me: bool, request: Request
    ) -> None:
        username = username.strip()
        user = await _find_admin(or_(User.username == username, User.email == username))
        if user is None or not verify_password(password, user.hashed_password):
            raise LoginFailed(
                "Usuario o contraseña inválidos, o la cuenta no es administradora."
            )
        request.session[SESSION_KEY] = user.id

    async def authenticate(self, request: Request) -> AdminUser | None:
        user_id = request.session.get(SESSION_KEY)
        if user_id is None:
            return None
        user = await _find_admin(User.id == user_id)
        if user is None:
            request.session.pop(SESSION_KEY, None)
            return None
        return AdminUser(username=user.username)

    async def logout(self, request: Request) -> None:
        request.session.pop(SESSION_KEY, None)
