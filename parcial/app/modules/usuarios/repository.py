"""Repositorios del módulo usuarios y auditoría de seguridad (Ejercicios 6 y 7).

- UsuarioRepository: búsqueda por email.
- AsignacionRolRepository: roles vigentes, asignaciones abiertas y conteo de administradores.
- IntentoAccesoRepository: conteo de fallos recientes posteriores al último éxito (RN-07).
- registrar_intento_acceso_independiente: única escritura con sesión propia (Ejercicio 7).
- EventoSeguridadRepository: auditoría transaccional y listado paginado.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlmodel import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        email_limpio = email.strip().lower()
        stmt = select(Usuario).where(Usuario.email == email_limpio)
        resultado = await self.session.exec(stmt)
        return resultado.first()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AsignacionRol)

    async def get_by_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        stmt = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.id)
        )
        resultado = await self.session.exec(stmt)
        return list(resultado.all())

    async def get_roles_vigentes_nombres(
        self, usuario_id: int, ahora: datetime | None = None
    ) -> list[str]:
        if ahora is None:
            ahora = datetime.now(UTC)
        stmt = (
            select(AsignacionRol.rol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .where(AsignacionRol.revocada_en.is_(None))
            .where(or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > ahora))
            .order_by(AsignacionRol.rol)
        )
        resultado = await self.session.exec(stmt)
        return list(resultado.all())

    async def get_abierta_por_usuario_y_rol(
        self, usuario_id: int, rol: str
    ) -> AsignacionRol | None:
        stmt = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .where(AsignacionRol.rol == rol)
            .where(AsignacionRol.revocada_en.is_(None))
        )
        resultado = await self.session.exec(stmt)
        return resultado.first()

    async def contar_admins_vigentes(
        self, ahora: datetime | None = None, excluir_usuario_id: int | None = None
    ) -> int:
        if ahora is None:
            ahora = datetime.now(UTC)
        stmt = (
            select(func.count(func.distinct(AsignacionRol.usuario_id)))
            .select_from(AsignacionRol)
            .join(Usuario, AsignacionRol.usuario_id == Usuario.id)
            .where(Usuario.activo.is_(True))
            .where(AsignacionRol.rol == "ADMIN")
            .where(AsignacionRol.revocada_en.is_(None))
            .where(or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > ahora))
        )
        if excluir_usuario_id is not None:
            stmt = stmt.where(AsignacionRol.usuario_id != excluir_usuario_id)
        total = await self.session.scalar(stmt)
        return int(total or 0)


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IntentoAcceso)

    async def contar_fallos_recientes(
        self, email: str, ip: str, ventana_desde: datetime
    ) -> int:
        email_limpio = email.strip().lower()
        # 1. Buscar último éxito dentro de la ventana (RN-07)
        stmt_exito = (
            select(func.max(IntentoAcceso.cuando))
            .where(IntentoAcceso.email == email_limpio)
            .where(IntentoAcceso.ip == ip)
            .where(IntentoAcceso.exito.is_(True))
            .where(IntentoAcceso.cuando >= ventana_desde)
        )
        ultimo_exito = await self.session.scalar(stmt_exito)

        # 2. Contar fallos posteriores al último éxito dentro de la ventana
        stmt_fallos = (
            select(func.count())
            .select_from(IntentoAcceso)
            .where(IntentoAcceso.email == email_limpio)
            .where(IntentoAcceso.ip == ip)
            .where(IntentoAcceso.exito.is_(False))
            .where(IntentoAcceso.cuando >= ventana_desde)
        )
        if ultimo_exito is not None:
            stmt_fallos = stmt_fallos.where(IntentoAcceso.cuando > ultimo_exito)

        total = await self.session.scalar(stmt_fallos)
        return int(total or 0)

    async def calcular_retry_after(
        self, email: str, ip: str, ventana_desde: datetime, ventana_segundos: int = 60
    ) -> int:
        """Calcula los segundos restantes para la cabecera Retry-After."""
        email_limpio = email.strip().lower()
        stmt = (
            select(IntentoAcceso.cuando)
            .where(IntentoAcceso.email == email_limpio)
            .where(IntentoAcceso.ip == ip)
            .where(IntentoAcceso.exito.is_(False))
            .where(IntentoAcceso.cuando >= ventana_desde)
            .order_by(IntentoAcceso.cuando.asc())
            .limit(1)
        )
        primer_fallo = await self.session.scalar(stmt)
        if primer_fallo is not None:
            ahora = datetime.now(UTC)
            if primer_fallo.tzinfo is None:
                primer_fallo = primer_fallo.replace(tzinfo=UTC)
            transcurrido = int((ahora - primer_fallo).total_seconds())
            restante = max(1, ventana_segundos - transcurrido)
            return min(restante, ventana_segundos)
        return ventana_segundos


# Comentario obligatorio de 3 puntos (Ejercicio 7, pág. 12 del PDF):
# 1. Qué hace distinto: Es la única escritura de todo el sistema que abre su propia
#    AsyncSession y su propia transacción desde session_factory y ejecuta commit() inmediatamente.
# 2. Por qué no puede compartir la transacción: Porque el intento fallido de login
#    termina lanzando 401 NoAutenticado (lo cual revierte o descarta la transacción
#    de la petición), y el fallo que se quiere contar para el límite de RN-07 es justamente
#    el que sobreviviría sólo si se confirma en una transacción independiente.
# 3. Cuál es su costo: Consume una transacción/conexión adicional breve y deja filas
#    confirmadas en intento_acceso aunque el resto de la petición falle o sea rechazada.
async def registrar_intento_acceso_independiente(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    ip: str,
    exito: bool,
) -> IntentoAcceso:
    async with session_factory() as sesion_propia:
        intento = IntentoAcceso(email=email.strip().lower(), ip=ip, exito=exito)
        sesion_propia.add(intento)
        await sesion_propia.commit()
        return intento


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventoSeguridad)

    async def listar_paginado(self, offset: int, limit: int) -> list[EventoSeguridad]:
        stmt = (
            select(EventoSeguridad)
            .order_by(EventoSeguridad.id.desc())
            .offset(offset)
            .limit(limit)
        )
        resultado = await self.session.exec(stmt)
        return list(resultado.all())
