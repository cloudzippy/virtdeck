from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

__all__ = ["get_db", "get_current_user", "require_role", "CurrentUser"]


class CurrentUser:
    def __init__(self, id: str, role: Role) -> None:
        self.id = id
        self.role = role


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc
    return CurrentUser(id=payload["sub"], role=Role(payload["role"]))


def require_role(*allowed: Role) -> Callable[[CurrentUser], CurrentUser]:
    """Dependency factory: 403s unless the current user's role is in `allowed`."""

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permissions"
            )
        return user

    return _checker
