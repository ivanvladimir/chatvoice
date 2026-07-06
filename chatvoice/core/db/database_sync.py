from contextlib import contextmanager

from sqlalchemy import  create_engine
from sqlalchemy.orm import  sessionmaker


from ..db import Base
from ...models import *
from ..config import settings, DatabaseOption

if settings.DATABASE == DatabaseOption.SQLITE:
    DATABASE_URI = settings.SQLITE_URI
    DATABASE_PREFIX = settings.SQLITE_SYNC_PREFIX
elif settings.DATABASE ==  DatabaseOption.MYSQL:
    DATABASE_URI = settings.MYSQL_URI
    DATABASE_PREFIX = settings.MYSQL_SYNC_PREFIX
elif settings.DATABASE == DatabaseOption.POSTGRES:
    DATABASE_URI = settings.POSTGRES_URI
    DATABASE_PREFIX = settings.POSTGRES_SYNC_PREFIX
DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"

engine = create_engine(DATABASE_URL, echo=False, future=True)

local_session = sessionmaker(engine)

@contextmanager
def get_db_ctx():
    db = local_session()
    try:
        yield db
        db.commit()    # commit if no exceptions
    except Exception:
        db.rollback()  # rollback on error
        raise
    finally:
        db.close()    # always close the session

def init_db():
    Base.metadata.create_all(bind=engine)

