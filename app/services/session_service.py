"""Creación, validación y revocación de sesiones (tokens JWT activos).

Autor: David Armando Olmos Moreno
"""
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import LoginSession, User
from app.security import create_access_token, decode_access_token, hash_token
from app.utils import utcnow


class InvalidTokenError(Exception):
    """El token no es válido, expiró o fue revocado."""


def create_session(db: Session, user: User) -> str:
    """Emite un JWT nuevo y registra la sesión en ``login_sessions``."""
    token, expires_at = create_access_token(user.id)
    # Limpieza: borra sesiones vencidas de este usuario.
    db.query(LoginSession).filter(
        LoginSession.user_id == user.id, LoginSession.expires_at < utcnow()
    ).delete()
    db.add(LoginSession(user_id=user.id, token=hash_token(token), expires_at=expires_at))
    db.commit()
    return token


def validate_token(db: Session, token: str) -> LoginSession:
    """Valida firma, expiración Y que la sesión siga activa en la BD.

    Que el JWT sea válido no basta: si hicieron logout la fila ya no existe y
    el token queda revocado aunque no haya vencido.
    """
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise InvalidTokenError("Token inválido o expirado")
    session = db.query(LoginSession).filter(LoginSession.token == hash_token(token)).first()
    if session is None or session.expires_at < utcnow():
        raise InvalidTokenError("Sesión cerrada o expirada")
    if str(session.user_id) != payload.get("sub"):
        raise InvalidTokenError("Token inválido")
    return session


def revoke_session(db: Session, session: LoginSession) -> None:
    """Revoca el token eliminando su sesión."""
    db.delete(session)
    db.commit()


def expires_in_seconds() -> int:
    """Segundos de vida de un token nuevo (para la respuesta)."""
    return settings.access_token_minutes * 60
