from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import router as api_router
from .front import router as front_router
from .core.setup import create_application, lifespan_factory
from .core.config import get_settings  # wherever get_settings lives


def create_app() -> FastAPI:
    """Factory that builds the FastAPI app. Importable by uvicorn."""
    settings = get_settings()
    admin = None

    @asynccontextmanager
    async def lifespan_with_admin(app: FastAPI) -> AsyncGenerator[None, None]:
        default_lifespan = lifespan_factory(settings)
        async with default_lifespan(app):
            if admin:
                await admin.initialize()
            yield

    return create_application(
        api_router=api_router,
        front_router=front_router,
        settings=settings,
        lifespan=lifespan_with_admin,
    )
