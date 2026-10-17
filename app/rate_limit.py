"""Rate limiting en memoria (ventana deslizante) para endpoints críticos.

Autor: David Armando Olmos Moreno
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import settings


class RateLimiter:
    """Cuenta peticiones por clave dentro de una ventana de tiempo."""

    def __init__(self) -> None:
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Registra una petición. Devuelve False si ya se superó el límite."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()  # descarta peticiones fuera de la ventana
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        """Borra todos los contadores (útil en pruebas)."""
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(name: str, limit: int, window_seconds: int):
    """Crea una dependencia de FastAPI que limita ``limit`` peticiones por IP en la ventana."""

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = request.client.host if request.client else "desconocida"
        if not limiter.hit(f"{name}:{ip}", limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes. Intenta de nuevo en un momento.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
