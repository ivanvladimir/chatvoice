from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .admin.initialize import create_admin_interface
from .api import router as api_router
from .core.config import get_settings  # wherever get_settings lives
from .core.setup import create_application, lifespan_factory
from .front import router as front_router


def create_app() -> FastAPI:
    """Factory that builds the FastAPI app. Importable by uvicorn."""
    settings = get_settings()
    admin = create_admin_interface()

    @asynccontextmanager
    async def lifespan_with_admin(app: FastAPI) -> AsyncGenerator[None, None]:
        default_lifespan = lifespan_factory(settings)
        async with default_lifespan(app):
            if admin:
                await admin.initialize()
            yield

    app = create_application(
        api_router=api_router,
        front_router=front_router,
        settings=settings,
        lifespan=lifespan_with_admin,
    )

    if admin:
        app.mount(settings.CRUD_ADMIN_MOUNT_PATH, admin.app)

    return app
