"""Esquemas Pydantic (validación de entrada y salida) con ejemplos para /docs.

Autor: David Armando Olmos Moreno
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class _EmailModel(BaseModel):
    """Base con un campo email validado y normalizado a minúsculas."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        """Normaliza el correo para que 'A@x.com' y 'a@x.com' sean el mismo usuario."""
        return value.lower()


class UserCreate(_EmailModel):
    """Datos para registrar un usuario."""

    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "david@example.com",
                "password": "Segura1234",
                "full_name": "David Olmos",
            }
        }
    )

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        """Exige letra + número y un máximo de 72 bytes (límite de bcrypt)."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes")
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("La contraseña debe tener al menos una letra y un número")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Quita espacios sobrantes y evita nombres vacíos."""
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre es demasiado corto")
        return value


class LoginRequest(_EmailModel):
    """Credenciales para iniciar sesión (primer factor)."""

    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "david@example.com", "password": "Segura1234"}}
    )


class OTPVerifyRequest(_EmailModel):
    """Correo + código OTP recibido por email (segundo factor)."""

    code: str = Field(pattern=r"^\d{6}$")

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "david@example.com", "code": "123456"}}
    )


class ResendOTPRequest(_EmailModel):
    """Solicitud para reenviar un código OTP."""

    model_config = ConfigDict(json_schema_extra={"example": {"email": "david@example.com"}})


class ProfileUpdate(BaseModel):
    """Campos que el usuario puede cambiar de su perfil."""

    full_name: str = Field(min_length=2, max_length=120)

    model_config = ConfigDict(json_schema_extra={"example": {"full_name": "David Armando Olmos"}})

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Quita espacios sobrantes y evita nombres vacíos."""
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre es demasiado corto")
        return value


class UserOut(BaseModel):
    """Usuario tal como lo devuelve la API (nunca incluye el hash)."""

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "david@example.com",
                "full_name": "David Olmos",
                "created_at": "2026-10-17T15:00:00",
                "updated_at": "2026-10-17T15:00:00",
            }
        },
    )


class TokenResponse(BaseModel):
    """Respuesta con el JWT de acceso."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta que el token expira")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"access_token": "eyJhbGciOi...", "token_type": "bearer", "expires_in": 1800}
        }
    )


class MessageResponse(BaseModel):
    """Respuesta simple con un mensaje."""

    message: str

    model_config = ConfigDict(json_schema_extra={"example": {"message": "Operación exitosa"}})
