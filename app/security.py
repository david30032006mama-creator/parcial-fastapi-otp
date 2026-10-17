"""Funciones de seguridad: hash de contraseñas (bcrypt) y tokens JWT.

Autor: David Armando Olmos Moreno
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Genera el hash bcrypt (con sal aleatoria incluida) de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash. Devuelve False si el hash es inválido."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Hash de relleno: se usa cuando el usuario no existe para que login tarde casi
# lo mismo con usuarios existentes y no existentes (evita enumerar cuentas).
DUMMY_PASSWORD_HASH = hash_password("contrasena-de-relleno-1")


def create_access_token(user_id: int):
    """Crea un JWT firmado con claims ``sub``, ``iat``, ``exp`` y ``jti``.

    Returns:
        (token, expires_at): el JWT y su vencimiento como datetime UTC naive.
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires,
        "jti": secrets.token_hex(8),  # id único: dos tokens nunca son idénticos
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires.replace(tzinfo=None)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida firma + expiración. Lanza ``jwt.PyJWTError`` si es inválido."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"require": ["exp", "sub"]},
    )


def hash_token(token: str) -> str:
    """SHA-256 del JWT. Se guarda esto en la BD, nunca el token completo."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
