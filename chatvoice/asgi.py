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

    app = create_application(
        api_router=api_router,
        front_router=front_router,
        settings=settings,
        lifespan=lifespan_factory(settings),
    )

    if admin:
        admin.mount_to(app)

    return app
