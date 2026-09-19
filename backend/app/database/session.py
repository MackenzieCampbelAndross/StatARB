from typing import Generator
from sqlalchemy.orm import Session
from app.database.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used in FastAPI endpoints with Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
