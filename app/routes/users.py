"""Endpoints de usuario (requieren autenticación).

Autor: David Armando Olmos Moreno
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_user
from app.models import User
from app.schemas import ProfileUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/profile", response_model=UserOut, summary="Ver mi perfil")
def get_profile(current_user: User = Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado (sin el hash de contraseña)."""
    return current_user


@router.put("/profile", response_model=UserOut, summary="Actualizar mi perfil")
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza el nombre del usuario autenticado."""
    current_user.full_name = payload.full_name
    db.commit()
    db.refresh(current_user)
    return current_user
