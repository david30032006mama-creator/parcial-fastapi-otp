# Guion de sustentación individual

> Está escrito en primera persona para que lo estudies y lo digas con tus palabras.
> Antes de sustentar: abre cada archivo, lee el código y ejecuta `pytest -v` y el flujo
> en `/docs` hasta que puedas explicar cada parte sin leer. Completa los datos
> marcados con [ ] (URL del despliegue, tus commits reales).

Duración sugerida: 8 a 10 minutos. Orden de la rúbrica: comprensión del código,
contribución individual, seguridad y despliegue (2.5 puntos cada una).

---

## 1. Comprensión del código (2.5 pts)

**Idea general.** Construí una API con FastAPI donde iniciar sesión tiene dos pasos:
primero contraseña y después un código OTP de 6 dígitos que llega al correo. Solo con
el OTP correcto se entrega un JWT, y ese JWT se usa para las rutas protegidas.

**Flujo completo, paso a paso.**
1. `POST /auth/register`: valido el correo y la contraseña con Pydantic, guardo el
   usuario con la contraseña hasheada con bcrypt.
2. `POST /auth/login`: busco al usuario y comparo la contraseña con su hash. Si es
   correcta, `otp_service.create_otp` genera un código, lo guarda con vencimiento de
   15 minutos y `email_service` lo envía por SMTP.
3. `POST /auth/verify-otp`: `otp_service.verify_otp` revisa que el código exista, no
   esté usado, no haya vencido y coincida. Lo marca como usado y `session_service`
   crea el JWT y registra la sesión en `login_sessions`.
4. En cada petición protegida, el `AuthMiddleware` valida el token antes de llegar a la
   ruta.
5. `POST /auth/logout` borra la sesión: el token queda revocado.

**Qué hace cada archivo.**
- `config.py`: lee las variables de entorno en un objeto `settings`. Si falta
  `SECRET_KEY` en producción, la app no arranca.
- `database.py`: crea el engine de SQLite, la fábrica de sesiones y `get_db`, que abre
  y cierra una sesión por petición.
- `models.py`: las tres tablas del enunciado (`users`, `otp_codes`, `login_sessions`)
  con sus relaciones.
- `schemas.py`: validación de entrada/salida con Pydantic y ejemplos para Swagger.
  `UserOut` nunca incluye el hash.
- `security.py`: `hash_password`/`verify_password` (bcrypt), `create_access_token` y
  `decode_access_token` (JWT) y `hash_token` (SHA-256).
- `otp_service.py`: genera el código con PyOTP, lo guarda como HMAC y lo valida.
- `email_service.py`: arma el correo con `EmailMessage` y lo envía con `smtplib`.
  Si falla lanza `EmailDeliveryError` y la ruta responde 503.
- `session_service.py`: crea, valida y revoca sesiones.
- `middleware.py`: el middleware y las dependencias `get_current_user` y
  `get_current_session_id`.
- `rate_limit.py`: ventana deslizante en memoria, por IP y por endpoint.
- `routes/auth.py` y `routes/users.py`: los 8 endpoints del enunciado.
- `main.py`: crea la app, registra middleware y rutas, crea las tablas al arrancar y
  define el manejador de errores 422.

**Decisiones que puedo justificar.**
- *¿Por qué guardar el hash del token y no el token?* Si alguien lee la base de datos
  no puede usar los tokens. Pasa lo mismo con el OTP, que guardo como HMAC.
- *¿Por qué revisar la BD si el JWT ya es válido?* Porque un JWT no se puede "borrar".
  Para que el logout funcione, el token debe existir también en `login_sessions`.
- *¿Por qué un middleware y además dependencias?* El middleware valida el token una
  sola vez para todo un grupo de rutas; las dependencias entregan el usuario a cada
  ruta y hacen que Swagger muestre el botón "Authorize".
- *¿Por qué `used` en el OTP?* Para que cada código sirva una sola vez.

---

## 2. Contribución individual (2.5 pts)

Mi parte fue: [describe con tus palabras qué módulos escribiste]. La evidencia está en:
- El historial de commits en GitHub (pestaña *Commits* / *Contributors*), con un
  commit por etapa: configuración, modelos, seguridad, OTP y correo, rutas, pruebas,
  documentación y despliegue.
- El docstring de cada archivo, que lleva `Autor: David Armando Olmos Moreno`.
- `CONTRIBUCIONES.md`: tabla por integrante y tabla de cumplimiento del enunciado.

Si me preguntan por una función específica, abro el archivo y la explico línea por
línea. Para probar que entiendo el código puedo hacer una modificación en vivo, por
ejemplo cambiar la vigencia del OTP con `OTP_EXPIRE_MINUTES`.

---

## 3. Seguridad (2.5 pts)

| Amenaza | Cómo la cubrí | Dónde |
|---|---|---|
| Robo de la base de datos | Contraseñas con bcrypt; OTP en HMAC; token solo como hash SHA-256 | `security.py`, `otp_service.py`, `session_service.py` |
| Adivinar el OTP | Solo 6 dígitos, por eso: vence en 15 min, un solo uso y máximo 5 intentos por minuto por IP | `otp_service.py`, `rate_limit.py` |
| Fuerza bruta en login | Rate limit de 5/min y mensaje genérico | `routes/auth.py` |
| Saber qué correos existen | Mismo error en login para usuario inexistente y contraseña mala, bcrypt de relleno para igualar tiempos, `resend-otp` responde igual | `routes/auth.py`, `security.py` |
| Token robado o logout | JWT con `exp`; sesión revocable; `refresh` rota el token | `session_service.py` |
| Rutas sin autenticación | `AuthMiddleware` valida firma, expiración y sesión activa | `middleware.py` |
| Fuga de información | Los 422 no devuelven el valor enviado; los logs no incluyen contraseñas, tokens ni OTP | `main.py`, `email_service.py` |
| Secretos en el repositorio | Variables de entorno; `.env` en `.gitignore` | `config.py`, `.gitignore` |

**Limitaciones que reconozco (conviene decirlas yo antes de que pregunten).**
El rate limiter está en memoria, así que no se comparte entre varios procesos; en
producción usaría Redis. Tampoco bloqueo la cuenta tras varios OTP fallidos: lo
cubre el límite por IP, pero un atacante con muchas IP sería más difícil de frenar.
SQLite es suficiente para el parcial, pero en producción usaría PostgreSQL.

---

## 4. Despliegue (2.5 pts)

- Plataforma: [Render / Railway / otra]. URL: [ ].
- Archivos: `requirements.txt` (versiones fijas), `.env.example`, `Procfile` y
  `render.yaml`. Arranco con Gunicorn y workers de Uvicorn.
- Variables de entorno configuradas en el panel de la plataforma (no en el código):
  `APP_ENV=production`, `SECRET_KEY` y la configuración de correo.
- Evidencia: logs de despliegue exitoso [captura] y `/health` respondiendo `ok`.

**Demostración en vivo** (en `[URL]/docs`):
1. `POST /auth/register` con mi correo.
2. `POST /auth/login` y mostrar el correo con el OTP.
3. `POST /auth/verify-otp` y copiar el `access_token`.
4. Botón *Authorize*, pegar el token y ejecutar `GET /users/profile`.
5. `POST /auth/logout` y repetir `GET /users/profile`: responde 401.

**Pruebas.** Ejecuto `pytest -v`: 27 pruebas (15 unitarias y 12 de integración).
Usan una base de datos en memoria y un correo simulado, así no dependen de internet.

---

## Preguntas que pueden hacerme

- **¿Qué pasa si el OTP vence?** `verify_otp` compara `expires_at` con la hora actual
  y devuelve 400. Pido uno nuevo con `resend-otp`.
- **¿Qué pasa si pido dos OTP?** Al crear uno nuevo marco los anteriores como usados.
- **¿Cómo sé quién eres en una ruta protegida?** El middleware valida el token y guarda
  el `user_id` en `request.state`; `get_current_user` lo carga de la BD.
- **¿Qué contiene el JWT?** `sub` (id del usuario), `iat`, `exp` y `jti` (id único).
- **¿Por qué 401 y no 403?** 401 es "no autenticado"; 403 sería autenticado sin permiso.
- **¿Por qué 409 en el registro?** Porque el recurso ya existe (conflicto).
- **¿Qué cambiarías?** Redis para el rate limit, PostgreSQL, bloqueo por intentos
  fallidos de OTP y verificación del correo al registrarse.
- **¿Qué es `Depends`?** El mecanismo de FastAPI para inyectar dependencias: `get_db`,
  `get_current_user`, el rate limit.
