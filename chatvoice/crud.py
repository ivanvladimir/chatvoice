from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_identifier(db: Session, identifier: int):
    return db.query(models.User).filter(models.User.identifier == identifier).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(identifier=user.identifier, data=user.data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
