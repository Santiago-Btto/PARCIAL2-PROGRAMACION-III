"""Dependencias de autenticación y autorización (Ejercicios 4, 5 y 6).

- Todas las dependencias usan `SessionDep`, que es la MISMA sesión de petición
  que recibe el Unit of Work (Ejercicio 6, sección 6.7), evitando abrir dos
  conexiones del pool por petición.
- `get_usuario_actual` lee únicamente la cookie `access_token` (nunca la cabecera
  Authorization) y responde 401 si no hay cookie, si el token es inválido/venció,
  o si el usuario no existe o está inactivo.
- `verificar_cambio_password_resuelto` se monta una sola vez en el grupo de rutas
  protegidas de `main.py` y responde 403 si `debe_cambiar_password` es verdadero (RN-06).
- `requiere_rol(*roles)` consulta los roles vigentes en `asignacion_rol` en cada
  petición (RN-04) y responde 403 si el usuario no posee ninguno de los roles requeridos.
"""

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import or_
from sqlmodel import select

from app.core.database import SessionDep
from app.core.errores import NoAutenticado, Prohibido
from app.core.security import COOKIE_NAME, decodificar_token_acceso
from app.modules.usuarios.models import AsignacionRol, Usuario


async def obtener_payload_token(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise NoAutenticado("No hay sesión iniciada.")
    return decodificar_token_acceso(token)


async def get_usuario_actual(
    request: Request,
    session: SessionDep,
) -> Usuario:
    payload = await obtener_payload_token(request)
    sub = payload.get("sub")
    try:
        usuario_id = int(sub)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise NoAutenticado("Token de sesión inválido.") from exc

    usuario = await session.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise NoAutenticado("El usuario no existe o se encuentra inactivo.")
    return usuario


UsuarioActualDep = Annotated[Usuario, Depends(get_usuario_actual)]


async def get_roles_vigentes(
    usuario: UsuarioActualDep,
    session: SessionDep,
) -> list[str]:
    """Consulta en la base las filas de asignacion_rol vigentes del usuario actual:
    no revocadas (`revocada_en IS NULL`) y sin vencer (`vence_en IS NULL OR vence_en > now()`).
    """
    ahora = datetime.now(UTC)
    stmt = (
        select(AsignacionRol.rol)
        .where(AsignacionRol.usuario_id == usuario.id)
        .where(AsignacionRol.revocada_en.is_(None))  # type: ignore[union-attr]
        .where(
            or_(
                AsignacionRol.vence_en.is_(None),  # type: ignore[union-attr]
                AsignacionRol.vence_en > ahora,  # type: ignore[operator]
            )
        )
        .order_by(AsignacionRol.rol)
    )
    resultado = await session.exec(stmt)
    return list(resultado.all())


RolesVigentesDep = Annotated[list[str], Depends(get_roles_vigentes)]


async def verificar_cambio_password_resuelto(usuario: UsuarioActualDep) -> Usuario:
    """Control montado una sola vez en el grupo de rutas protegidas (RN-06, Ejercicio 5)."""
    if usuario.debe_cambiar_password:
        raise Prohibido(
            "Debés cambiar tu contraseña provisoria en /auth/cambiar-password antes de continuar."
        )
    return usuario


def requiere_rol(*roles_permitidos: str) -> Callable[..., Coroutine[Any, Any, Usuario]]:
    """Fábrica de dependencias de autorización (RN-04, Ejercicio 5).

    Verifica primero que el usuario esté autenticado (401), que no tenga el
    cambio de contraseña pendiente (403) y que tenga al menos uno de los roles
    indicados vigente en la base de datos en esta petición (403).
    """
    roles_set = set(roles_permitidos)

    async def _dependencia(
        usuario: Annotated[Usuario, Depends(verificar_cambio_password_resuelto)],
        roles_vigentes: RolesVigentesDep,
    ) -> Usuario:
        if not roles_set.intersection(roles_vigentes):
            raise Prohibido("No tenés permisos suficientes para realizar esta operación.")
        return usuario

    return _dependencia
