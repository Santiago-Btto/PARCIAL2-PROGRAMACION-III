"""Unit of Work del módulo usuarios (Ejercicio 6).

Agrupa los repositorios de usuarios, asignaciones_rol, intentos_acceso,
eventos_seguridad y clientes sobre la misma AsyncSession de la petición (SessionDep).
"""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.asignaciones_rol = AsignacionRolRepository(session)
        self.intentos_acceso = IntentoAccesoRepository(session)
        self.eventos_seguridad = EventoSeguridadRepository(session)
        self.clientes = BaseRepository(session, Cliente)


def get_usuarios_uow(session: SessionDep) -> UsuariosUnitOfWork:
    return UsuariosUnitOfWork(session)


UsuariosUoWDep = Annotated[UsuariosUnitOfWork, Depends(get_usuarios_uow)]
