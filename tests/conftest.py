"""Configuración compartida de pytest: BD en memoria, cliente HTTP y correo falso.

Autor: David Armando Olmos Moreno
"""
import os

# Estas variables deben fijarse ANTES de importar la aplicación.
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-pytest-0123456789abcdef"
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import limiter  # noqa: E402
from app.services import email_service  # noqa: E402


@pytest.fixture()
def db_session_factory():
    """BD SQLite en memoria, nueva y vacía para cada prueba."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session_factory, monkeypatch):
    """Cliente de pruebas con BD aislada, sin rate limit y con correo simulado.

    Los correos "enviados" quedan en ``client.sent_emails`` para leer el OTP.
    """

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    sent = []
    monkeypatch.setattr(
        email_service,
        "send_otp_email",
        lambda to_email, full_name, code: sent.append({"to": to_email, "code": code}),
    )
    monkeypatch.setattr(settings, "rate_limit_enabled", False)

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = db_session_factory
    limiter.reset()

    test_client = TestClient(app)
    test_client.sent_emails = sent
    yield test_client

    app.dependency_overrides.clear()
    app.state.session_factory = SessionLocal
