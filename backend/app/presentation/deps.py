from fastapi import Depends, HTTPException, Request
from typing import Any
from sqlalchemy.orm import Session
from app.application.services import AuthService, ChatService
from app.core.security import ACCESS_COOKIE
from app.domain.repositories import IUnitOfWork
from app.infrastructure.adapters.demo_assistant import DemoAssistant
from app.infrastructure.adapters.maira_assistant import MairaAssistant
from app.core.config import settings
from app.infrastructure.adapters.password_hasher import BcryptPasswordHasher
from app.infrastructure.adapters.password_verifier import BcryptPasswordVerifier
from app.infrastructure.database import get_db
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_uow(db: Session = Depends(get_db)) -> IUnitOfWork:
    return SqlAlchemyUnitOfWork(db)

def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()

def get_password_verifier() -> BcryptPasswordVerifier:
    return BcryptPasswordVerifier()

def get_assistant_provider():
    return MairaAssistant() if settings.maira_enabled else DemoAssistant()

def get_auth_service(uow: IUnitOfWork = Depends(get_uow), password_hasher: BcryptPasswordHasher = Depends(get_password_hasher), password_verifier: BcryptPasswordVerifier = Depends(get_password_verifier)) -> Any:
    return AuthService(uow, password_hasher, password_verifier)

def get_chat_service(uow: IUnitOfWork = Depends(get_uow), assistant: object = Depends(get_assistant_provider)) -> Any:
    return ChatService(uow, assistant)

def get_current_user(request: Request, service: Any = Depends(get_auth_service)):
    token = request.cookies.get(ACCESS_COOKIE)
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return service.current_user(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_roles(*roles: str):
    allowed = set(roles)
    def dependency(user=Depends(get_current_user)):
        current = user.role.value if hasattr(user.role, "value") else str(user.role)
        if current not in allowed:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return user
    return dependency
