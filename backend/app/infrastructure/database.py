import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

_engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 1800}
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(pool_size=int(os.getenv("DB_POOL_SIZE", "10")), max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")))
else:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
