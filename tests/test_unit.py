"""Pruebas unitarias: seguridad, OTP, rate limiter y validación de esquemas.

Autor: David Armando Olmos Moreno
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.config import settings
from app.models import OTPCode, User
from app.rate_limit import RateLimiter
from app.schemas import UserCreate
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services import otp_service
from app.utils import utcnow


@pytest.fixture()
def db_and_user(db_session_factory):
    """Sesión de BD con un usuario ya creado."""
    db = db_session_factory()
    user = User(email="ana@example.com", password_hash="x", full_name="Ana Prueba")
    db.add(user)
    db.commit()
    db.refresh(user)
    yield db, user
    db.close()


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("Segura1234")
    assert hashed != "Segura1234"
    assert hashed.startswith("$2")  # prefijo de bcrypt
    assert verify_password("Segura1234", hashed)
    assert not verify_password("OtraClave99", hashed)


def test_verify_password_with_malformed_hash_returns_false():
    assert verify_password("cualquiera1", "esto-no-es-un-hash") is False


def test_jwt_contains_expiration_and_subject():
    token, expires_at = create_access_token(7)
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert "exp" in payload and "jti" in payload
    assert expires_at > utcnow()


def test_expired_jwt_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_jwt_with_wrong_signature_is_rejected():
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "una-clave-distinta-de-al-menos-32-caracteres!!",
        algorithm=settings.algorithm,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_generated_otp_has_six_digits():
    for _ in range(50):
        code = otp_service.generate_code()
        assert len(code) == 6 and code.isdigit()


def test_otp_is_valid_once_only(db_and_user):
    db, user = db_and_user
    code = otp_service.create_otp(db, user)
    assert otp_service.verify_otp(db, user, code) is True
    assert otp_service.verify_otp(db, user, code) is False  # ya fue usado


def test_wrong_otp_is_rejected(db_and_user):
    db, user = db_and_user
    code = otp_service.create_otp(db, user)
    wrong = "000000" if code != "000000" else "111111"
    assert otp_service.verify_otp(db, user, wrong) is False


def test_expired_otp_is_rejected(db_and_user):
    db, user = db_and_user
    code = otp_service.create_otp(db, user)
    record = db.query(OTPCode).first()
    record.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert otp_service.verify_otp(db, user, code) is False


def test_otp_lasts_15_minutes_and_is_stored_hashed(db_and_user):
    db, user = db_and_user
    code = otp_service.create_otp(db, user)
    record = db.query(OTPCode).first()
    assert record.code != code and len(record.code) == 64  # HMAC, no el número
    lifetime = record.expires_at - record.created_at
    assert timedelta(minutes=14, seconds=55) <= lifetime <= timedelta(minutes=15, seconds=5)


def test_rate_limiter_blocks_after_limit():
    rl = RateLimiter()
    assert all(rl.hit("ip-1", 3, 60) for _ in range(3))
    assert rl.hit("ip-1", 3, 60) is False  # cuarta petición bloqueada
    assert rl.hit("ip-2", 3, 60) is True  # otra IP no se afecta


def test_weak_or_short_password_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="solo letras", full_name="Ana")
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="a1", full_name="Ana")
