"""Pruebas de integración: flujos completos contra la API (BD real en memoria).

Autor: David Armando Olmos Moreno
"""
from app.config import settings
from app.services import email_service

EMAIL = "david@example.com"
PASSWORD = "Segura1234"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post(
        "/auth/register", json={"email": email, "password": password, "full_name": "David Olmos"}
    )


def login_and_get_token(client):
    """Registra, hace login, lee el OTP del correo simulado y devuelve el JWT."""
    assert register(client).status_code == 201
    assert client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
    code = client.sent_emails[-1]["code"]
    response = client.post("/auth/verify-otp", json={"email": EMAIL, "code": code})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_full_authentication_flow(client):
    token = login_and_get_token(client)
    assert len(client.sent_emails) == 1 and client.sent_emails[0]["to"] == EMAIL

    profile = client.get("/users/profile", headers=auth(token))
    assert profile.status_code == 200
    assert profile.json()["email"] == EMAIL
    assert "password" not in profile.text

    assert client.post("/auth/logout", headers=auth(token)).status_code == 200
    # El token sigue sin vencer, pero ya fue revocado:
    assert client.get("/users/profile", headers=auth(token)).status_code == 401


def test_register_rejects_duplicates_and_invalid_data(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert register(client, email="no-es-un-correo").status_code == 422
    assert register(client, email="otro@example.com", password="corta1").status_code == 422


def test_validation_error_does_not_echo_the_password(client):
    response = register(client, password="corta1")
    assert response.status_code == 422
    assert "corta1" not in response.text


def test_login_with_wrong_credentials_gives_same_generic_error(client):
    register(client)
    wrong_password = client.post("/auth/login", json={"email": EMAIL, "password": "Incorrecta99"})
    unknown_user = client.post("/auth/login", json={"email": "nadie@example.com", "password": PASSWORD})
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert client.sent_emails == []  # sin credenciales válidas no se envía OTP


def test_login_returns_503_when_email_fails(client, monkeypatch):
    register(client)

    def failing_send(*_args):
        raise email_service.EmailDeliveryError("smtp caído")

    monkeypatch.setattr(email_service, "send_otp_email", failing_send)
    response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 503


def test_protected_routes_require_a_valid_token(client):
    for method, path in [
        ("get", "/users/profile"),
        ("put", "/users/profile"),
        ("post", "/auth/logout"),
        ("post", "/auth/refresh"),
    ]:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers=auth("token-falso")).status_code == 401


def test_otp_wrong_code_and_reuse_are_rejected(client):
    register(client)
    client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    code = client.sent_emails[-1]["code"]
    wrong = "000000" if code != "000000" else "111111"

    assert client.post("/auth/verify-otp", json={"email": EMAIL, "code": wrong}).status_code == 400
    assert client.post("/auth/verify-otp", json={"email": EMAIL, "code": code}).status_code == 200
    assert client.post("/auth/verify-otp", json={"email": EMAIL, "code": code}).status_code == 400


def test_resend_otp_invalidates_previous_code(client):
    register(client)
    client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    first = client.sent_emails[-1]["code"]
    assert client.post("/auth/resend-otp", json={"email": EMAIL}).status_code == 200
    second = client.sent_emails[-1]["code"]
    assert len(client.sent_emails) == 2

    if first != second:  # (1 en un millón de que coincidan)
        assert client.post("/auth/verify-otp", json={"email": EMAIL, "code": first}).status_code == 400
    assert client.post("/auth/verify-otp", json={"email": EMAIL, "code": second}).status_code == 200


def test_resend_otp_for_unknown_email_does_not_reveal_it(client):
    response = client.post("/auth/resend-otp", json={"email": "nadie@example.com"})
    assert response.status_code == 200
    assert client.sent_emails == []


def test_refresh_rotates_token_and_revokes_the_old_one(client):
    old_token = login_and_get_token(client)
    refreshed = client.post("/auth/refresh", headers=auth(old_token))
    assert refreshed.status_code == 200
    new_token = refreshed.json()["access_token"]
    assert new_token != old_token
    assert client.get("/users/profile", headers=auth(old_token)).status_code == 401
    assert client.get("/users/profile", headers=auth(new_token)).status_code == 200


def test_update_profile(client):
    token = login_and_get_token(client)
    response = client.put("/users/profile", headers=auth(token), json={"full_name": "David A. Olmos"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "David A. Olmos"
    assert client.get("/users/profile", headers=auth(token)).json()["full_name"] == "David A. Olmos"


def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    register(client)
    statuses = [
        client.post("/auth/login", json={"email": EMAIL, "password": "Incorrecta99"}).status_code
        for _ in range(7)
    ]
    assert statuses[:5] == [401] * 5
    assert statuses[5:] == [429, 429]
