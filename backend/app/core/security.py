import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Request, Response

from app.core.config import settings

ACCESS_COOKIE = "access_token_cookie"
REFRESH_COOKIE = "refresh_token_cookie"
ACCESS_CSRF_COOKIE = "csrf_access_token"
REFRESH_CSRF_COOKIE = "csrf_refresh_token"
ALGORITHM = "HS256"


def make_token(user_id: str, email: str, full_name: str, kind: str, lifetime: timedelta, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "fullName": full_name,
            "type": kind,
            "iat": now,
            "exp": now + lifetime,
            "jti": jti or secrets.token_urlsafe(32),
        },
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, kind: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != kind or not payload.get("sub"):
            raise ValueError("Token type mismatch")
        return payload
    except Exception as exc:
        raise ValueError("Invalid or expired token") from exc


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    access_csrf = secrets.token_urlsafe(32)
    refresh_csrf = secrets.token_urlsafe(32)
    common = {"secure": settings.cookie_secure, "samesite": settings.cookie_samesite.lower()}
    response.set_cookie(ACCESS_COOKIE, access, httponly=True, path="/", max_age=settings.jwt_access_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, path="/api/auth", max_age=settings.jwt_refresh_days * 86400, **common)
    response.set_cookie(ACCESS_CSRF_COOKIE, access_csrf, httponly=False, path="/", max_age=settings.jwt_access_minutes * 60, **common)
    response.set_cookie(REFRESH_CSRF_COOKIE, refresh_csrf, httponly=False, path="/", max_age=settings.jwt_refresh_days * 86400, **common)


def set_csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    common = {"secure": settings.cookie_secure, "samesite": settings.cookie_samesite.lower()}
    response.set_cookie(ACCESS_CSRF_COOKIE, token, httponly=False, path="/", max_age=settings.jwt_access_minutes * 60, **common)
    return token


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    response.delete_cookie(ACCESS_CSRF_COOKIE, path="/")
    response.delete_cookie(REFRESH_CSRF_COOKIE, path="/")


def require_csrf(request: Request, refresh: bool = False) -> None:
    if not settings.jwt_cookie_csrf_protect:
        return
    cookie_name = REFRESH_CSRF_COOKIE if refresh else ACCESS_CSRF_COOKIE
    expected = request.cookies.get(cookie_name)
    supplied = request.headers.get("X-CSRF-TOKEN")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
