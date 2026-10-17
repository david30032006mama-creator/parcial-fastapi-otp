# Sistema de Autenticación con OTP — FastAPI

Parcial de Desarrollo de Software. API REST con registro, login en dos pasos
(contraseña + código OTP por correo), JWT con expiración, rutas protegidas,
middleware de autenticación y cierre de sesión con revocación de token.

**Autor:** David Armando Olmos Moreno

## Stack

FastAPI · SQLAlchemy · SQLite · PyOTP · smtplib · PyJWT · bcrypt · pytest · Gunicorn/Uvicorn

## Estructura

```
app/
├── main.py            # aplicación, middleware, manejo de errores 422
├── config.py          # variables de entorno (.env)
├── database.py        # engine, sesión y Base de SQLAlchemy
├── models.py          # users, otp_codes, login_sessions
├── schemas.py         # esquemas Pydantic con ejemplos
├── security.py        # bcrypt y JWT
├── middleware.py      # AuthMiddleware + dependencias get_current_user
├── rate_limit.py      # rate limiting por IP
├── routes/
│   ├── auth.py        # register, login, verify-otp, resend-otp, refresh, logout
│   └── users.py       # GET/PUT /users/profile
└── services/
    ├── otp_service.py     # generar y validar OTP
    ├── email_service.py   # envío de correo (smtplib, o API Brevo)
    └── session_service.py # crear, validar y revocar sesiones
tests/                 # 15 unitarios + 12 de integración (pytest)
```

## Instalación local

```bash
git clone <URL-de-tu-repositorio>
cd parcial-fastapi-otp
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Edita `.env` y completa `SECRET_KEY` (el comando para generarla está en el archivo).
Para enviar correos reales completa `SMTP_*`. Si no configuras SMTP en
desarrollo, el código OTP se imprime en la consola del servidor.

```bash
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/docs (Swagger). Las tablas se crean solas al arrancar.

## Endpoints

| Método | Ruta | Descripción | Auth | Rate limit |
|---|---|---|---|---|
| POST | `/auth/register` | Registrar usuario | No | 10/min |
| POST | `/auth/login` | Valida credenciales y envía OTP | No | 5/min |
| POST | `/auth/verify-otp` | Verifica OTP y entrega JWT | No | 5/min |
| POST | `/auth/resend-otp` | Reenvía OTP | No | 3/min |
| POST | `/auth/refresh` | Nuevo JWT (revoca el anterior) | Sí | — |
| POST | `/auth/logout` | Cierra sesión y revoca el token | Sí | — |
| GET | `/users/profile` | Ver perfil | Sí | — |
| PUT | `/users/profile` | Actualizar nombre | Sí | — |
| GET | `/health` | Estado del servicio | No | — |

## Flujo de uso (curl)

```bash
curl -X POST $URL/auth/register -H "content-type: application/json" \
  -d '{"email":"david@example.com","password":"Segura1234","full_name":"David Olmos"}'

curl -X POST $URL/auth/login -H "content-type: application/json" \
  -d '{"email":"david@example.com","password":"Segura1234"}'      # llega el OTP al correo

curl -X POST $URL/auth/verify-otp -H "content-type: application/json" \
  -d '{"email":"david@example.com","code":"123456"}'              # devuelve access_token

curl $URL/users/profile -H "Authorization: Bearer <access_token>"
curl -X POST $URL/auth/logout -H "Authorization: Bearer <access_token>"
```

## Códigos de estado

200 OK · 201 creado · 400 OTP inválido/expirado · 401 sin token, token inválido/revocado
o credenciales incorrectas · 409 correo ya registrado · 422 datos inválidos ·
429 demasiadas solicitudes · 503 no se pudo enviar el correo.

## Seguridad

- Contraseñas con **bcrypt** (sal aleatoria). Mínimo 8 caracteres, letra y número.
- **OTP** de 6 dígitos (PyOTP), válido 15 min, de un solo uso; en la BD se guarda un
  HMAC-SHA256, no el número. Un OTP nuevo invalida los anteriores.
- **JWT** HS256 con `exp`, `iat`, `sub` y `jti`. La BD guarda solo su hash SHA-256 en
  `login_sessions`; borrar la fila revoca el token (logout) aunque no haya vencido.
- **Middleware** que valida el token (firma, expiración y sesión activa) antes de las
  rutas protegidas.
- **Rate limiting** en register, login, verify-otp y resend-otp.
- Mensajes genéricos ("Credenciales inválidas", "Código inválido o expirado") y
  verificación bcrypt de relleno para no revelar si un correo existe.
- Los errores 422 no devuelven el valor enviado (no se filtra la contraseña) y los logs
  nunca incluyen contraseñas, tokens ni OTP (salvo la consola de desarrollo sin SMTP).
- Secretos solo en variables de entorno; `.env` está en `.gitignore`.

## Pruebas

```bash
pytest -v
```

27 pruebas: 15 unitarias (hash, JWT, OTP, rate limiter, esquemas, servicio de correo)
y 12 de integración (flujo completo, errores, revocación, refresh, rate limit).

## Despliegue

Variables de entorno necesarias: `APP_ENV=production`, `SECRET_KEY` y la configuración
de correo. Comando de arranque (también en `Procfile`):

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:$PORT --forwarded-allow-ips="*" app.main:app
```

Pasos detallados en `GUIA_GITHUB_Y_DESPLIEGUE.md`.

> **Limitaciones conocidas:** el rate limiter vive en memoria (por eso `-w 1`) y SQLite
> es un archivo local: en plataformas con disco efímero los datos se reinician en cada
> despliegue. Para producción real se usaría Redis y PostgreSQL.

## Contribuciones

Ver `CONTRIBUCIONES.md` (tabla por integrante) y el historial de commits.
