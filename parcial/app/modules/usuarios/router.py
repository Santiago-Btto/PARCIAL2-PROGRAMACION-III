"""Rutas HTTP de autenticación, usuarios, roles y auditoría (Ejercicios 4, 5, 6 y 7).

- auth_router (/auth): registro, login con cookie HttpOnly, logout, perfil yo y cambio de clave.
- usuarios_router (/usuarios): gestión de personal y asignación/revocación de roles (ADMIN).
- eventos_router (/eventos): auditoría de seguridad paginada (ADMIN).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response

from app.core.dependencies import (
    UsuarioActualDep,
    obtener_payload_token,
    requiere_rol,
)
from app.core.paginacion import PageQuery, Pagina, SizeQuery
from app.core.parametros import IdPath
from app.core.security import borrar_cookie_acceso, setear_cookie_acceso
from app.modules.usuarios import service
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.schemas import (
    AsignacionRolOut,
    AsignarRolIn,
    CambiarPasswordIn,
    EventoSeguridadOut,
    LoginIn,
    LoginOut,
    LogoutOut,
    RegistroIn,
    UsuarioCreateIn,
    UsuarioOut,
    YoOut,
)
from app.modules.usuarios.unit_of_work import UsuariosUoWDep

AdminActualDep = Annotated[Usuario, Depends(requiere_rol("ADMIN"))]

# --- Rutas de Autenticación y Cuenta (/auth) ---

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/registro", status_code=201, response_model=UsuarioOut)
async def registro(datos: RegistroIn, uow: UsuariosUoWDep) -> UsuarioOut:
    """Auto-registro público de clientes (RN-02 y Caso C-02)."""
    return await service.registrar_cliente(uow, datos)


@auth_router.post("/login", status_code=200, response_model=LoginOut)
async def login(
    request: Request,
    response: Response,
    datos: LoginIn,
    uow: UsuariosUoWDep,
) -> LoginOut:
    """Inicio de sesión con emisión de JWT en cookie HttpOnly (RN-07, RN-08 y Caso C-03)."""
    ip = request.client.host if request.client else "127.0.0.1"
    session_factory = request.app.state.session_factory
    dummy_password_hash = getattr(request.app.state, "dummy_password_hash", "")
    token, expira_en_segundos, login_out = await service.iniciar_sesion(
        uow=uow,
        session_factory=session_factory,
        datos=datos,
        ip=ip,
        dummy_password_hash=dummy_password_hash,
    )
    setear_cookie_acceso(response, token, expira_en_segundos)
    return login_out


@auth_router.post("/logout", status_code=200, response_model=LogoutOut)
async def logout(response: Response) -> LogoutOut:
    """Cierre de sesión: elimina la cookie access_token."""
    borrar_cookie_acceso(response)
    return LogoutOut(mensaje="Sesión cerrada")


@auth_router.get("/yo", status_code=200, response_model=YoOut)
async def yo(
    uow: UsuariosUoWDep,
    usuario: UsuarioActualDep,
    payload: Annotated[dict[str, Any], Depends(obtener_payload_token)],
) -> YoOut:
    """Consulta del perfil autenticado con roles vigentes en base vs roles en token."""
    return await service.obtener_perfil_yo(uow, usuario, payload)


@auth_router.post("/cambiar-password", status_code=200)
async def cambiar_password_endpoint(
    uow: UsuariosUoWDep,
    usuario: UsuarioActualDep,
    datos: CambiarPasswordIn,
) -> dict[str, str]:
    """Cambio obligatorio o voluntario de contraseña (RN-06, RN-16 y Caso C-09)."""
    return await service.cambiar_password(uow, usuario, datos)


# --- Gestión de Personal y Roles (/usuarios) ---

usuarios_router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@usuarios_router.post("", status_code=201, response_model=UsuarioOut)
async def crear_personal_endpoint(
    uow: UsuariosUoWDep,
    admin: AdminActualDep,
    datos: UsuarioCreateIn,
) -> UsuarioOut:
    """Alta de usuario con rol de personal (RN-01, RN-16)."""
    return await service.crear_personal(uow, admin, datos)


@usuarios_router.get("/{id}/roles", status_code=200, response_model=list[AsignacionRolOut])
async def listar_roles(
    id: IdPath,
    uow: UsuariosUoWDep,
    admin: AdminActualDep,
) -> list[AsignacionRol]:
    """Lista las asignaciones de rol de un usuario."""
    return await service.listar_roles_usuario(uow, id)


@usuarios_router.post("/{id}/roles", status_code=201, response_model=AsignacionRolOut)
async def asignar_rol_endpoint(
    id: IdPath,
    datos: AsignarRolIn,
    uow: UsuariosUoWDep,
    admin: AdminActualDep,
) -> AsignacionRol:
    """Asignación de un nuevo rol con vigencia (RN-03, RN-16 y Caso C-07)."""
    return await service.asignar_rol(uow, admin, id, datos)


@usuarios_router.delete("/{id}/roles/{rol}", status_code=200, response_model=AsignacionRolOut)
async def revocar_rol_endpoint(
    id: IdPath,
    rol: str,
    uow: UsuariosUoWDep,
    admin: AdminActualDep,
) -> AsignacionRol:
    """Revocación de un rol vigente (RN-05, RN-16 y Casos C-07 y C-08)."""
    return await service.revocar_rol(uow, admin, id, rol)


# --- Auditoría de Seguridad (/eventos) ---

eventos_router = APIRouter(
    prefix="/eventos",
    tags=["eventos"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@eventos_router.get("", status_code=200, response_model=Pagina[EventoSeguridadOut])
async def listar_eventos_endpoint(
    uow: UsuariosUoWDep,
    admin: AdminActualDep,
    page: PageQuery = 1,
    size: SizeQuery = 20,
) -> Pagina[EventoSeguridadOut]:
    """Listado paginado de eventos de seguridad (RN-16)."""
    return await service.listar_eventos(uow, page=page, size=size)
