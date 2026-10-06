from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.contrib.sqla import Admin

from ..core.config import EnvironmentOption, settings
from ..core.db.database import async_engine
from .auth import AdminAuthProvider
from .views import register_admin_views


def create_admin_interface() -> Admin | None:
    """Create and configure the starlette-admin interface (None if disabled)."""
    if not settings.ADMIN_ENABLED:
        return None

    secret_key = settings.SECRET_KEY.get_secret_value()
    admin = Admin(
        async_engine,
        title="Chatvoice Admin",
        base_url=settings.ADMIN_MOUNT_PATH,
        auth_provider=AdminAuthProvider(),
        secret_key=secret_key,
        middlewares=[
            # Holds the admin login; separate cookie from the main app's auth
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie="chatvoice_admin_session",
                max_age=settings.ADMIN_SESSION_TIMEOUT * 60,
                # The path the browser sees: behind a proxy prefix (ROOT_PATH,
                # e.g. /l52mas/chatvoice) a bare "/admin" would never match.
                path=(settings.ROOT_PATH or "").rstrip("/") + settings.ADMIN_MOUNT_PATH,
                https_only=settings.SESSION_SECURE_COOKIES
                and settings.ENVIRONMENT != EnvironmentOption.LOCAL,
            )
        ],
    )

    register_admin_views(admin)

    return admin
