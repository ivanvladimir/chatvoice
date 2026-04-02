from core.logger import setup_logging, get_logger
from models import *
from core.db.database_sync import engine, Base 

class Console():
    def __init__(self, 
                 log,
                 name: str = "chatvoice",
                 ):
        Base.metadata.create_all(bind=engine)
        log.info("Initialized database tables")


