from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from collections.abc import Callable
from typing import TypeVar
T = TypeVar("T")
from app.domain.errors.conflict_error import ConflictError
from app.domain.repositories import IUnitOfWork as ILegacyUnitOfWork
from app.domain.ports.i_unit_of_work import IUnitOfWork
from app.infrastructure.repositories import (
    SqlAlchemyConversationRepository, SqlAlchemyMessageRepository,
    SqlAlchemyRefreshTokenRepository, SqlAlchemyUserRepository,
)

class SqlAlchemyUnitOfWork(ILegacyUnitOfWork, IUnitOfWork):
    def __init__(self, db: Session):
        self.db = db
        self.users = SqlAlchemyUserRepository(db)
        self.conversations = SqlAlchemyConversationRepository(db)
        self.messages = SqlAlchemyMessageRepository(db)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepository(db)
    def run(self, work: Callable[[], T], conflict_message: str | None = None) -> T:
        try:
            result = work()
            self.db.commit()
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_message or "A record with these details already exists") from exc
        except Exception:
            self.db.rollback()
            raise

    def commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("A record with these details already exists") from exc
    def rollback(self) -> None: self.db.rollback()
    def refresh(self, entity: object) -> None: self.db.refresh(entity)
    def flush(self) -> None: self.db.flush()
