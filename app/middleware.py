"""Middleware de autenticación y dependencias para rutas protegidas.

Un middleware real (``AuthMiddleware``) intercepta las peticiones a rutas
protegidas, valida el token Bearer y deja el id de usuario en ``request.state``.
Las dependencias ``get_current_user`` y ``get_current_session_id`` lo leen.

Autor: David Armando Olmos Moreno
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import get_db
from app.models import User
from app.services.session_service import InvalidTokenError, validate_token

# Rutas que exigen token. Todo lo demás es público.
PROTECTED_PREFIXES = ("/users", "/auth/refresh", "/auth/logout")

# Solo sirve para que Swagger (/docs) muestre el botón "Authorize".
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Obtiene el token del header ``Authorization: Bearer <token>``."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _validate_sync(session_factory, token: str):
    """Valida el token con su propia sesión de BD (se ejecuta en un hilo aparte)."""
    db = session_factory()
    try:
        session = validate_token(db, token)
        return session.user_id, session.id
    finally:
        db.close()


def _unauthorized(detail: str) -> JSONResponse:
    """Respuesta 401 estándar con el header WWW-Authenticate."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Valida el JWT antes de que la petición llegue a las rutas protegidas."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method != "OPTIONS" and path.startswith(PROTECTED_PREFIXES):
            token = _extract_bearer_token(request)
            if token is None:
                return _unauthorized("Token de autenticación no proporcionado")
            try:
                user_id, session_id = await run_in_threadpool(
                    _validate_sync, request.app.state.session_factory, token
                )
            except InvalidTokenError as exc:
                return _unauthorized(str(exc))
            request.state.user_id = user_id
            request.state.session_id = session_id
        return await call_next(request)


def get_current_session_id(request: Request, _credentials=Depends(bearer_scheme)) -> int:
    """Id de la sesión autenticada (lo dejó el middleware)."""
    session_id = getattr(request.state, "session_id", None)
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    return session_id


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    _credentials=Depends(bearer_scheme),
) -> User:
    """Usuario autenticado de la petición actual."""
    user_id = getattr(request.state, "user_id", None)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    return user
