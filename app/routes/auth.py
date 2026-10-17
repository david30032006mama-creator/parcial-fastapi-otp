"""Endpoints de autenticación: registro, login con OTP, refresh y logout.

Autor: David Armando Olmos Moreno
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_session_id, get_current_user
from app.models import LoginSession, User
from app.rate_limit import rate_limit
from app.schemas import (
    LoginRequest,
    MessageResponse,
    OTPVerifyRequest,
    ResendOTPRequest,
    TokenResponse,
    UserCreate,
    UserOut,
)
from app.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.services import email_service, otp_service, session_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _issue_otp(db: Session, user: User) -> None:
    """Crea un OTP y lo envía por correo. Lanza EmailDeliveryError si falla."""
    code = otp_service.create_otp(db, user)
    email_service.send_otp_email(user.email, user.full_name, code)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    dependencies=[Depends(rate_limit("register", 10, 60))],
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Crea un usuario. El correo debe ser válido y no estar registrado (409 si ya existe)."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # dos registros simultáneos con el mismo correo
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=MessageResponse,
    summary="Login con usuario y contraseña (envía el OTP)",
    dependencies=[Depends(rate_limit("login", 5, 60))],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Primer factor: valida correo + contraseña y envía un OTP de 6 dígitos por email."""
    user = db.query(User).filter(User.email == payload.email).first()
    # Se hace siempre una verificación bcrypt (aunque el usuario no exista) para
    # que el tiempo de respuesta no revele si el correo está registrado.
    password_ok = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        _issue_otp(db, user)
    except email_service.EmailDeliveryError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo enviar el código. Intenta más tarde.")
    return MessageResponse(message="Código OTP enviado al correo registrado")


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verificar el OTP y obtener el JWT",
    dependencies=[Depends(rate_limit("verify-otp", 5, 60))],
)
def verify_otp(payload: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Segundo factor: si el código es correcto y vigente, devuelve un JWT con expiración."""
    user = db.query(User).filter(User.email == payload.email).first()
    # Mismo mensaje para "usuario inexistente", "código malo" y "código vencido".
    if user is None or not otp_service.verify_otp(db, user, payload.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código OTP inválido o expirado")
    token = session_service.create_session(db, user)
    return TokenResponse(access_token=token, expires_in=session_service.expires_in_seconds())


@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    summary="Reenviar el código OTP",
    dependencies=[Depends(rate_limit("resend-otp", 3, 60))],
)
def resend_otp(payload: ResendOTPRequest, db: Session = Depends(get_db)):
    """Genera y envía un OTP nuevo (invalida el anterior).

    Responde igual exista o no el correo, para no revelar qué cuentas existen.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        try:
            _issue_otp(db, user)
        except email_service.EmailDeliveryError:
            logger.error("No se pudo reenviar el OTP")
    return MessageResponse(message="Si el correo está registrado, se envió un nuevo código")


@router.post("/refresh", response_model=TokenResponse, summary="Refrescar el token JWT")
def refresh(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    session_id: int = Depends(get_current_session_id),
):
    """Emite un token nuevo y revoca el anterior (rotación de tokens)."""
    old_session = db.get(LoginSession, session_id)
    if old_session is not None:
        session_service.revoke_session(db, old_session)
    token = session_service.create_session(db, user)
    return TokenResponse(access_token=token, expires_in=session_service.expires_in_seconds())


@router.post("/logout", response_model=MessageResponse, summary="Cerrar sesión y revocar el token")
def logout(
    db: Session = Depends(get_db),
    session_id: int = Depends(get_current_session_id),
):
    """Elimina la sesión: el token deja de funcionar aunque no haya vencido."""
    session = db.get(LoginSession, session_id)
    if session is not None:
        session_service.revoke_session(db, session)
    return MessageResponse(message="Sesión cerrada correctamente")
