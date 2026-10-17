"""Aplicación principal FastAPI: sistema de autenticación con OTP.

Autor: David Armando Olmos Moreno
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registra las tablas en Base.metadata)
from app.database import Base, SessionLocal, engine
from app.middleware import AuthMiddleware
from app.routes import auth, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Al arrancar, crea las tablas si no existen."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="API de Autenticación con OTP",
    description=(
        "Registro, login con contraseña + código OTP por correo, JWT con expiración, "
        "rutas protegidas y cierre de sesión con revocación de token."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# El middleware usa esta fábrica de sesiones (las pruebas la reemplazan).
app.state.session_factory = SessionLocal
app.add_middleware(AuthMiddleware)

app.include_router(auth.router)
app.include_router(users.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    """Respuesta 422 sin ``input``: así la contraseña enviada no se devuelve en el error."""
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/", tags=["Estado"], summary="Estado del servicio")
def root():
    """Ruta raíz con un mensaje de bienvenida."""
    return {"service": "API de Autenticación con OTP", "docs": "/docs"}


@app.get("/health", tags=["Estado"], summary="Health check")
def health():
    """Usado por la plataforma de despliegue para comprobar que el servicio vive."""
    return {"status": "ok"}
