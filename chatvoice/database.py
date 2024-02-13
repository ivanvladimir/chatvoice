from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from .config import get_config

config = dict(get_config())

DB=config.get("db","./sql_app.db")
chat = config.get('entry_point',None)
if chat:
    db_filename=os.path.join(
            config.get("conversations_dir", "conversations"),
            chat,
            DB,
        )
else:
    db_filename=os.path.join(
            config.get("conversations_dir", "conversations"),
            f"conversations.db"
        )


SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_filename}"
# TODO: Addapt to use a formal database
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

