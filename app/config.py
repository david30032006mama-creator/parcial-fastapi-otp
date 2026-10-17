"""Configuración central de la aplicación.

Lee las variables de entorno (archivo .env en desarrollo) y las expone en un
único objeto ``settings``. Así ningún secreto queda escrito en el código.

Autor: David Armando Olmos Moreno
"""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _as_bool(value, default: bool) -> bool:
    """Convierte un texto de variable de entorno a booleano."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí"}


class Settings:
    """Contenedor de configuración leída del entorno."""

    def __init__(self) -> None:
        self.env = os.getenv("APP_ENV", "development").lower()

        secret = os.getenv("SECRET_KEY", "")
        if not secret:
            if self.env == "production":
                # En producción es obligatorio definir la clave: sin ella los
                # tokens serían inválidos al reiniciar el servidor.
                raise RuntimeError("SECRET_KEY es obligatoria en producción")
            secret = secrets.token_urlsafe(48)
            logger.warning("SECRET_KEY no definida: se usa una temporal (solo desarrollo).")
        self.secret_key = secret
        self.algorithm = "HS256"
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
        self.otp_minutes = int(os.getenv("OTP_EXPIRE_MINUTES", "15"))

        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")

        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", self.smtp_user)
        self.smtp_use_tls = _as_bool(os.getenv("SMTP_USE_TLS"), True)

        # "smtp" (smtplib, por defecto) o "brevo" (API HTTPS, para hostings que bloquean SMTP).
        self.email_backend = os.getenv("EMAIL_BACKEND", "smtp").lower()
        self.brevo_api_key = os.getenv("BREVO_API_KEY", "")

        self.rate_limit_enabled = _as_bool(os.getenv("RATE_LIMIT_ENABLED"), True)


settings = Settings()
