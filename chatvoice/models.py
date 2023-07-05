from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(Integer, unique=True, index=True)
    data = Column(String)
    is_active = Column(Boolean, default=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())

