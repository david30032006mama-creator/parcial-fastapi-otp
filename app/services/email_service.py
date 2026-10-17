"""Envío de correos con smtplib (librería estándar).

Autor: David Armando Olmos Moreno
"""
import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """No se pudo entregar el correo (SMTP caído, mal configurado, etc.)."""


def send_otp_email(to_email: str, full_name: str, code: str) -> None:
    """Envía el código OTP al correo del usuario.

    En desarrollo, si no hay SMTP configurado, el código se imprime en consola
    para poder probar. En producción NUNCA se escribe el código en los logs.

    Raises:
        EmailDeliveryError: si el envío falla.
    """
    if settings.email_backend == "brevo":
        _send_with_brevo(to_email, full_name, code)
        return

    if not settings.smtp_host:
        if settings.env == "production":
            logger.error("SMTP no configurado en producción")
            raise EmailDeliveryError("SMTP no configurado")
        logger.warning("[SOLO DESARROLLO] OTP para %s: %s", to_email, code)
        return

    message = EmailMessage()
    message["Subject"] = "Tu código de verificación"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email
    message.set_content(
        f"Hola {full_name},\n\n"
        f"Tu código de verificación es: {code}\n"
        f"Es válido por {settings.otp_minutes} minutos y solo puede usarse una vez.\n\n"
        "Si no fuiste tú, ignora este mensaje."
    )

    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        with server:
            if settings.smtp_port != 465 and settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        # Solo se registra el tipo de error: el mensaje podría incluir datos sensibles.
        logger.error("Fallo al enviar correo OTP (%s)", type(exc).__name__)
        raise EmailDeliveryError("No se pudo enviar el correo") from exc


def _send_with_brevo(to_email: str, full_name: str, code: str) -> None:
    """Alternativa por API HTTPS (Brevo) para hostings gratuitos que bloquean los puertos SMTP.

    Raises:
        EmailDeliveryError: si falta configuración o la API responde con error.
    """
    sender = settings.smtp_from or settings.smtp_user
    if not settings.brevo_api_key or not sender:
        logger.error("Brevo no configurado (BREVO_API_KEY / SMTP_FROM)")
        raise EmailDeliveryError("Brevo no configurado")
    body = json.dumps(
        {
            "sender": {"name": "Verificación", "email": sender},
            "to": [{"email": to_email, "name": full_name}],
            "subject": "Tu código de verificación",
            "textContent": (
                f"Hola {full_name}, tu código es: {code}. "
                f"Es válido por {settings.otp_minutes} minutos y solo puede usarse una vez."
            ),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=body,
        method="POST",
        headers={
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15):
            pass
    except (urllib.error.URLError, OSError) as exc:
        logger.error("Fallo al enviar correo OTP por Brevo (%s)", type(exc).__name__)
        raise EmailDeliveryError("No se pudo enviar el correo") from exc
