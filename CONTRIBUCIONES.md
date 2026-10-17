# Contribuciones y trazabilidad

> Ajusta la primera tabla a lo que realmente hizo cada integrante. La evidencia real
> es el historial de commits (`git log --author`, o la pestaña *Contributors* de GitHub).

## 1. Contribución por integrante

| Integrante | Módulos / archivos | Endpoints | Pruebas | Evidencia (commits) |
|---|---|---|---|---|
| David Armando Olmos Moreno | `config.py`, `database.py`, `models.py`, `schemas.py`, `security.py`, `rate_limit.py`, `middleware.py`, `main.py`, `routes/`, `services/` | Todos | `tests/` (27) | Ver `git log` (un commit por etapa) |
| (integrante 2 — completar si aplica) | | | | |
| (integrante 3 — completar si aplica) | | | | |

Autoría también declarada en el docstring de cada módulo (`Autor: ...`).

## 2. Cumplimiento del enunciado

| # | Requisito del parcial | Dónde está | Prueba que lo valida |
|---|---|---|---|
| 1 | Registro con validación de email | `routes/auth.py::register`, `schemas.py::UserCreate` (EmailStr) | `test_register_rejects_duplicates_and_invalid_data` |
| 2 | Login con usuario y contraseña | `routes/auth.py::login` | `test_login_with_wrong_credentials_gives_same_generic_error` |
| 3 | OTP de 6 dígitos válido 15 min | `services/otp_service.py` | `test_generated_otp_has_six_digits`, `test_otp_lasts_15_minutes_and_is_stored_hashed` |
| 4 | Envío de OTP por correo | `services/email_service.py` (smtplib) | `test_smtp_backend_sends_message_with_code` |
| 5 | Verificación de OTP | `routes/auth.py::verify_otp`, `otp_service.verify_otp` | `test_otp_wrong_code_and_reuse_are_rejected`, `test_expired_otp_is_rejected` |
| 6 | JWT con expiración | `security.py::create_access_token` | `test_jwt_contains_expiration_and_subject`, `test_expired_jwt_is_rejected` |
| 7 | Rutas protegidas | `routes/users.py`, `/auth/refresh`, `/auth/logout` | `test_protected_routes_require_a_valid_token` |
| 8 | Middleware que valida tokens | `middleware.py::AuthMiddleware` | `test_protected_routes_require_a_valid_token` |
| 9 | Logout con revocación de token | `routes/auth.py::logout`, `session_service.revoke_session` | `test_full_authentication_flow` |
| 10 | Errores y códigos HTTP adecuados | 200/201/400/401/409/422/429/503 | `test_validation_error_does_not_echo_the_password`, `test_login_returns_503_when_email_fails` |
| 11 | Hash con bcrypt | `security.py::hash_password` | `test_password_is_hashed_and_verifiable` |
| 12 | Rate limiting | `rate_limit.py` | `test_rate_limit_returns_429`, `test_rate_limiter_blocks_after_limit` |
| 13 | No exponer datos sensibles | handler 422 en `main.py`, logs sin secretos | `test_validation_error_does_not_echo_the_password` |
| 14 | Tablas users, otp_codes, login_sessions | `models.py` | todos los de integración |
| 15 | Endpoints obligatorios (8) | `routes/auth.py`, `routes/users.py` | `tests/test_integration.py` |
| 16 | Docstrings, README, comentarios | todo el código, `README.md` | — |
| 17 | ≥5 unitarias y ≥3 de integración | `tests/` (15 + 12) | `pytest -v` |
| 18 | Despliegue con requirements, .env y Gunicorn/Uvicorn | `requirements.txt`, `.env.example`, `Procfile`, `render.yaml` | Ver sección de despliegue del README |
