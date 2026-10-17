"""Utilidades pequeñas compartidas por todo el proyecto.

Autor: David Armando Olmos Moreno
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Devuelve la hora UTC actual SIN zona horaria (naive).

    SQLite no guarda zona horaria, así que usamos siempre datetimes naive en
    UTC para poder compararlos sin errores.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
