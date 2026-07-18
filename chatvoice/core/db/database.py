from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..config import settings, DatabaseOption

if settings.DATABASE == DatabaseOption.SQLITE:
    DATABASE_URI = settings.SQLITE_URI
    DATABASE_PREFIX = settings.SQLITE_ASYNC_PREFIX
elif settings.DATABASE == DatabaseOption.MYSQL:
    DATABASE_URI = settings.MYSQL_URI
    DATABASE_PREFIX = settings.MYSQL_ASYNC_PREFIX
elif settings.DATABASE == DatabaseOption.POSTGRES:
    DATABASE_URI = settings.POSTGRES_URI
    DATABASE_PREFIX = settings.POSTGRES_ASYNC_PREFIX
DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

local_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as db:
        yield db
