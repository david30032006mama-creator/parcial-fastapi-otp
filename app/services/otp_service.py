"""Generación y validación de códigos OTP.

Autor: David Armando Olmos Moreno
"""
import hashlib
import hmac
from datetime import timedelta

import pyotp
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OTPCode, User
from app.utils import utcnow


def _hash_code(code: str) -> str:
    """HMAC-SHA256 del código usando SECRET_KEY: en la BD nunca queda el código en claro."""
    return hmac.new(settings.secret_key.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_code() -> str:
    """Genera un código numérico de 6 dígitos con PyOTP (secreto aleatorio nuevo cada vez)."""
    totp = pyotp.TOTP(pyotp.random_base32(), digits=6, interval=settings.otp_minutes * 60)
    return totp.now()


def create_otp(db: Session, user: User) -> str:
    """Crea un OTP nuevo para el usuario e invalida los anteriores no usados.

    Returns:
        El código en claro, solo para enviarlo por correo (no se almacena así).
    """
    db.query(OTPCode).filter(OTPCode.user_id == user.id, OTPCode.used.is_(False)).update(
        {"used": True}
    )
    code = generate_code()
    db.add(
        OTPCode(
            user_id=user.id,
            code=_hash_code(code),
            expires_at=utcnow() + timedelta(minutes=settings.otp_minutes),
        )
    )
    db.commit()
    return code


def verify_otp(db: Session, user: User, code: str) -> bool:
    """Valida el código contra el OTP vigente más reciente del usuario.

    Reglas: debe existir, no estar usado, no estar vencido y coincidir. Si es
    correcto se marca como usado (un OTP sirve una sola vez).
    """
    record = (
        db.query(OTPCode)
        .filter(OTPCode.user_id == user.id, OTPCode.used.is_(False))
        .order_by(OTPCode.id.desc())
        .first()
    )
    if record is None or record.expires_at < utcnow():
        return False
    # compare_digest evita ataques de temporización al comparar.
    if not hmac.compare_digest(record.code, _hash_code(code)):
        return False
    record.used = True
    db.commit()
    return True
