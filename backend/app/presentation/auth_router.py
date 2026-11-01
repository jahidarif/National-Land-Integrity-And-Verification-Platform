from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.core.security import set_csrf_cookie
from typing import Any
from app.core.security import REFRESH_COOKIE, clear_auth_cookies, require_csrf, set_auth_cookies
from app.presentation.deps import get_auth_service
from app.presentation.schemas import LoginRequest, RegisterRequest
from app.presentation.serializers import user_response

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/csrf")
def csrf(response: Response):
    return {"csrfToken": set_csrf_cookie(response)}

@router.post("/register", status_code=201)
def register(data: RegisterRequest, request: Request, service: Any = Depends(get_auth_service)):
    require_csrf(request)
    try:
        return user_response(service.register(data.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, service: Any = Depends(get_auth_service)):
    require_csrf(request)
    try:
        account = service.authenticate(data.email, data.password)
        access, refresh = service.tokens(account)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    set_auth_cookies(response, access, refresh)
    return user_response(account)

@router.post("/refresh")
def refresh(request: Request, response: Response, service: Any = Depends(get_auth_service)):
    require_csrf(request, refresh=True)
    token = request.cookies.get(REFRESH_COOKIE)
    if not token: raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        account, access, refreshed = service.refresh(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    set_auth_cookies(response, access, refreshed)
    return user_response(account)

@router.post("/logout")
def logout(request: Request, response: Response, service: Any = Depends(get_auth_service)):
    require_csrf(request)
    service.logout(request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response)
    return {"message": "Logged out"}

@router.get("/me")
def me(request: Request, service: Any = Depends(get_auth_service)):
    token = request.cookies.get("access_token_cookie")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return user_response(service.current_user(token))
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
