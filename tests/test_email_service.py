"""Pruebas del servicio de correo (sin enviar correos reales).

Autor: David Armando Olmos Moreno
"""
import pytest

from app.config import settings
from app.services import email_service


class _FakeSMTP:
    """SMTP falso que guarda lo que se le pide enviar."""

    sent = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, message):
        _FakeSMTP.sent.append(message)


def test_smtp_backend_sends_message_with_code(monkeypatch):
    _FakeSMTP.sent = []
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_user", "app@example.com")
    monkeypatch.setattr(email_service.smtplib, "SMTP", _FakeSMTP)
    email_service.send_otp_email("destino@example.com", "Ana", "123456")
    assert len(_FakeSMTP.sent) == 1
    assert _FakeSMTP.sent[0]["To"] == "destino@example.com"
    assert "123456" in _FakeSMTP.sent[0].get_content()


def test_missing_smtp_in_production_raises(monkeypatch):
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "env", "production")
    with pytest.raises(email_service.EmailDeliveryError):
        email_service.send_otp_email("a@b.com", "Ana", "123456")


def test_brevo_backend_posts_to_https_api(monkeypatch):
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["key"] = request.get_header("Api-key")
        return _Response()

    monkeypatch.setattr(settings, "email_backend", "brevo")
    monkeypatch.setattr(settings, "brevo_api_key", "clave-falsa")
    monkeypatch.setattr(settings, "smtp_from", "app@example.com")
    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)
    email_service.send_otp_email("destino@example.com", "Ana", "654321")
    assert captured["url"].startswith("https://api.brevo.com/")
    assert captured["key"] == "clave-falsa"
