# Guía: subir a GitHub y desplegar

## 0. Importante
Tu repositorio `kairos-web` es del parcial de Tecnologías Web. **Este parcial va en un
repositorio nuevo** (por ejemplo `parcial-fastapi-otp`), no mezcles los dos.

## 1. Crear el repositorio vacío
1. En GitHub: botón **+** → **New repository**.
2. Nombre: `parcial-fastapi-otp`. Público o privado según pida tu docente.
3. **No** marques README, .gitignore ni licencia (el proyecto ya los trae). **Create repository**.

## 2. Subir el proyecto con commits por etapa
Descomprime el ZIP, abre una terminal dentro de la carpeta `parcial-fastapi-otp` y ejecuta:

```bash
git init -b main
git config user.name "David Armando Olmos Moreno"
git config user.email "tu-correo-de-github@ejemplo.com"

git add .gitignore requirements.txt .env.example pytest.ini
git commit -m "chore: dependencias, .gitignore y plantilla de variables de entorno"

git add app/__init__.py app/config.py app/utils.py app/database.py app/models.py
git commit -m "feat: configuración y modelos (users, otp_codes, login_sessions)"

git add app/schemas.py app/security.py
git commit -m "feat: esquemas Pydantic, hash bcrypt y tokens JWT"

git add app/services/__init__.py app/services/otp_service.py app/services/email_service.py app/services/session_service.py
git commit -m "feat: servicios de OTP, correo y sesiones"

git add app/rate_limit.py app/middleware.py
git commit -m "feat: rate limiting y middleware de autenticación"

git add app/routes app/main.py
git commit -m "feat: endpoints de autenticación y usuarios"

git add tests pytest.ini
git commit -m "test: 15 pruebas unitarias y 12 de integración"

git add README.md SUSTENTACION.md CONTRIBUCIONES.md GUIA_GITHUB_Y_DESPLIEGUE.md Procfile render.yaml
git commit -m "docs: README, sustentación, contribuciones y despliegue"

git remote add origin https://github.com/TU-USUARIO/parcial-fastapi-otp.git
git push -u origin main
```

Cambia `TU-USUARIO` por tu usuario. Si `git add` de algún archivo da error, ejecuta
`git status` para ver qué falta y agrégalo en el commit que corresponda.

**Autenticación al hacer push:** GitHub ya no acepta la contraseña de la cuenta. Al
ejecutar `git push`, Git Credential Manager (viene con Git para Windows) abre una
ventana para iniciar sesión con el navegador. Si te pide usuario y contraseña en la
terminal, usa un *Personal Access Token* (GitHub → Settings → Developer settings →
Personal access tokens) como contraseña.

**Revisa que `.env` NO se subió:** en la página del repositorio no debe aparecer ese
archivo (sí `.env.example`). Si lo subiste por error, cambia todas las claves.

Para los siguientes cambios: `git add .` → `git commit -m "mensaje"` → `git push`.

## 3. Correo con Gmail (SMTP)
1. Activa la verificación en 2 pasos en tu cuenta de Google.
2. Crea una **contraseña de aplicación** (Cuenta de Google → Seguridad → Contraseñas de aplicaciones).
3. Variables: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=tu@gmail.com`,
   `SMTP_PASSWORD=<contraseña de aplicación>`, `SMTP_FROM=tu@gmail.com`.

## 4. Desplegar en Render
1. Entra a render.com con tu cuenta de GitHub → **New +** → **Web Service** → elige el repositorio.
2. Runtime **Python 3**. Build Command: `pip install -r requirements.txt`.
3. Start Command:
   `gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:$PORT --forwarded-allow-ips="*" app.main:app`
4. Health Check Path: `/health`.
5. En **Environment** agrega: `APP_ENV=production`, `SECRET_KEY` (genérala con
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`) y las variables de correo.
6. **Create Web Service**. Cuando termine, abre `https://TU-SERVICIO.onrender.com/docs`.
7. Guarda capturas de la pestaña **Logs** con el despliegue exitoso (lo pide el enunciado).

### ⚠️ Correo en el plan gratuito de Render
Render **bloquea los puertos SMTP (25, 465 y 587) en los servicios web gratuitos** desde
septiembre de 2025; con SMTP el login fallaría con 503. Tienes dos caminos:
- **Instancia de pago** (desde unos 7 USD/mes): los puertos 465 y 587 funcionan.
- **Plan gratuito + API HTTPS de Brevo** (ya incluida en el código): crea una cuenta en
  brevo.com, verifica un remitente y genera una API key. En Render define
  `EMAIL_BACKEND=brevo`, `BREVO_API_KEY=<tu key>` y `SMTP_FROM=<remitente verificado>`.
  Aclara en la sustentación que el envío principal es `smtplib` y que Brevo es el
  respaldo para hostings que bloquean SMTP.

Otras notas del plan gratuito: el servicio se duerme tras ~15 minutos sin uso (la primera
petición tarda) y el disco es efímero: la base SQLite se reinicia en cada despliegue,
así que tendrás que volver a registrar el usuario de la demostración.

## 5. Otras plataformas
- **Railway:** New Project → Deploy from GitHub repo; el `Procfile` ya define el arranque.
  Agrega las mismas variables. Verifica si tu plan permite SMTP saliente.
- **PythonAnywhere:** el soporte para FastAPI (ASGI) es **beta** y hay que pedir que lo
  habiliten escribiendo a support@pythonanywhere.com; además las cuentas gratuitas solo
  acceden a sitios en lista blanca. Por eso recomiendo Render o Railway.

## 6. Checklist final
- [ ] Repositorio nuevo con commits por etapa y sin `.env`
- [ ] `pytest -v` pasa (27 pruebas)
- [ ] URL pública funcionando en `/docs` y `/health`
- [ ] Probado el flujo completo (register → login → OTP en el correo → profile → logout)
- [ ] Capturas de logs de despliegue
- [ ] `[ ]` de `SUSTENTACION.md` completados y `CONTRIBUCIONES.md` ajustado a tu equipo
