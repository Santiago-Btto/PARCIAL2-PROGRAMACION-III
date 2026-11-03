"""Servicio de autenticación, usuarios, roles y auditoría (Ejercicios 4, 5, 6 y 7).

- Todo cálculo bcrypt corre fuera del bucle de eventos ANTES de abrir el UnitOfWork.
- Toda operación multi-tabla se ejecuta de forma atómica en un único UnitOfWork.
- Los intentos de login se registran en una sesión/transacción independiente (Ejercicio 7).
- Autorización y vigencia de roles consultadas en la base de datos (RN-04).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import (
    Conflicto,
    DatosInvalidos,
    DemasiadosIntentos,
    MapaRestricciones,
    NoAutenticado,
    NoEncontrado,
    traducir_integrity_error,
)
from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.core.security import crear_token_acceso, hashear_password, verificar_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import ROLES_SISTEMA, AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.repository import registrar_intento_acceso_independiente
from app.modules.usuarios.schemas import (
    AsignacionRolOut,
    AsignarRolIn,
    CambiarPasswordIn,
    EventoSeguridadOut,
    LoginIn,
    LoginOut,
    RegistroIn,
    UsuarioCreateIn,
    UsuarioOut,
    YoOut,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

_MAPA_RESTRICCIONES_USUARIOS: MapaRestricciones = {
    "uq_usuario_email": (Conflicto, "Ya existe un usuario registrado con ese correo electrónico."),
    "uq_cliente_email": (Conflicto, "Ya existe un cliente registrado con ese correo electrónico."),
    "cliente_email_key": (Conflicto, "Ya existe un cliente registrado con ese correo electrónico."),
    "uq_cliente_usuario_id": (Conflicto, "El usuario ya tiene una ficha de cliente asociada."),
    "uq_asignacion_rol_usuario_rol_abierta": (
        Conflicto,
        "El usuario ya tiene una asignación abierta para ese rol.",
    ),
    "ck_asignacion_rol_rol_valido": (DatosInvalidos, "El rol indicado no es válido."),
}


# --- Autenticación y Cuentas (/auth) ---


async def registrar_cliente(uow: UsuariosUnitOfWork, datos: RegistroIn) -> UsuarioOut:
    """Auto-registro de un cliente por la web (RN-02 y Ejercicio 4).

    Calcula el hash bcrypt ANTES de abrir el UnitOfWork para no retener la conexión.
    Crea Usuario, AsignacionRol(rol='CLIENTE') y Cliente de forma atómica.
    """
    pwd_hash = await hashear_password(datos.password)

    try:
        async with uow:
            usuario = Usuario(
                email=datos.email,
                nombre=datos.nombre,
                password_hash=pwd_hash,
                activo=True,
                debe_cambiar_password=False,
            )
            await uow.usuarios.add(usuario)

            asignacion = AsignacionRol(
                usuario_id=usuario.id,  # type: ignore[arg-type]
                rol="CLIENTE",
            )
            await uow.asignaciones_rol.add(asignacion)

            cliente = Cliente(
                nombre=datos.nombre,
                email=datos.email,
                usuario_id=usuario.id,
            )
            await uow.clientes.add(cliente)
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, _MAPA_RESTRICCIONES_USUARIOS) from exc

    return UsuarioOut.model_validate(usuario)


async def iniciar_sesion(
    uow: UsuariosUnitOfWork,
    session_factory: async_sessionmaker[AsyncSession],
    datos: LoginIn,
    ip: str,
    dummy_password_hash: str,
) -> tuple[str, int, LoginOut]:
    """Inicio de sesión con cookie HttpOnly (RN-07, RN-08 y Ejercicio 7)."""
    ahora = datetime.now(UTC)
    ventana_desde = ahora - timedelta(seconds=60)

    # Paso 1 (RN-07): Límite de intentos sin invocar bcrypt
    fallos = await uow.intentos_acceso.contar_fallos_recientes(datos.email, ip, ventana_desde)
    if fallos >= 5:
        retry_after = await uow.intentos_acceso.calcular_retry_after(datos.email, ip, ventana_desde)
        raise DemasiadosIntentos(
            "Demasiados intentos fallidos. Intentá de nuevo más tarde.", retry_after=retry_after
        )

    # Paso 2 (RN-08): Búsqueda y verificación en tiempo constante
    usuario = await uow.usuarios.get_by_email(datos.email)
    if usuario is None:
        await verificar_password(datos.password, dummy_password_hash)
        await registrar_intento_acceso_independiente(
            session_factory, email=datos.email, ip=ip, exito=False
        )
        raise NoAutenticado("Credenciales inválidas.")

    es_valida = await verificar_password(datos.password, usuario.password_hash)
    if not es_valida or not usuario.activo:
        await registrar_intento_acceso_independiente(
            session_factory, email=datos.email, ip=ip, exito=False
        )
        raise NoAutenticado("Credenciales inválidas.")

    # Paso 3: Registro de login exitoso (reinicia la cuenta en RN-07)
    await registrar_intento_acceso_independiente(
        session_factory, email=datos.email, ip=ip, exito=True
    )

    # Paso 4: Consulta de roles vigentes para el payload del token
    roles_vigentes = await uow.asignaciones_rol.get_roles_vigentes_nombres(usuario.id, ahora)  # type: ignore[arg-type]

    # Paso 5: Emisión de token JWT (el token NO va en el cuerpo JSON, va en la cookie)
    token, expira_en_segundos = crear_token_acceso(usuario.id, roles_vigentes)  # type: ignore[arg-type]
    login_out = LoginOut(
        mensaje="Sesión iniciada",
        debe_cambiar_password=usuario.debe_cambiar_password,
        expira_en_segundos=expira_en_segundos,
    )
    return token, expira_en_segundos, login_out


async def obtener_perfil_yo(
    uow: UsuariosUnitOfWork, usuario_actual: Usuario, payload_token: dict[str, Any]
) -> YoOut:
    """Perfil del usuario autenticado (GET /auth/yo)."""
    roles_vigentes = await uow.asignaciones_rol.get_roles_vigentes_nombres(usuario_actual.id)  # type: ignore[arg-type]
    roles_token = list(payload_token.get("roles", []))
    return YoOut(
        id=usuario_actual.id,  # type: ignore[arg-type]
        email=usuario_actual.email,
        nombre=usuario_actual.nombre,
        activo=usuario_actual.activo,
        debe_cambiar_password=usuario_actual.debe_cambiar_password,
        roles_vigentes=roles_vigentes,
        roles_token=roles_token,
    )


async def cambiar_password(
    uow: UsuariosUnitOfWork, usuario_actual: Usuario, datos: CambiarPasswordIn
) -> dict[str, str]:
    """Cambio de contraseña (RN-06, RN-16)."""
    # Verificar contraseña actual ANTES de abrir la transacción
    es_valida = await verificar_password(datos.password_actual, usuario_actual.password_hash)
    if not es_valida:
        raise NoAutenticado("La contraseña actual es incorrecta.")

    nuevo_hash = await hashear_password(datos.password_nueva)

    async with uow:
        await uow.usuarios.update(
            usuario_actual,
            {"password_hash": nuevo_hash, "debe_cambiar_password": False},
        )
        evento = EventoSeguridad(
            actor=usuario_actual.email,
            accion="Cambio de contraseña",
        )
        await uow.eventos_seguridad.add(evento)

    return {"mensaje": "Contraseña modificada correctamente."}


# --- Gestión de Personal y Roles (/usuarios) ---


async def crear_personal(
    uow: UsuariosUnitOfWork, admin_actual: Usuario, datos: UsuarioCreateIn
) -> UsuarioOut:
    """Alta de usuario de personal (RN-01, RN-16)."""
    pwd_hash = await hashear_password(datos.password_provisoria)

    try:
        async with uow:
            usuario = Usuario(
                email=datos.email,
                nombre=datos.nombre,
                password_hash=pwd_hash,
                activo=True,
                debe_cambiar_password=True,
            )
            await uow.usuarios.add(usuario)

            asignacion = AsignacionRol(
                usuario_id=usuario.id,  # type: ignore[arg-type]
                rol=datos.rol,
                otorgada_por=admin_actual.id,
            )
            await uow.asignaciones_rol.add(asignacion)

            evento = EventoSeguridad(
                actor=admin_actual.email,
                accion=f"Alta de usuario {usuario.email} con rol {datos.rol}",
            )
            await uow.eventos_seguridad.add(evento)
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, _MAPA_RESTRICCIONES_USUARIOS) from exc

    return UsuarioOut.model_validate(usuario)


async def listar_roles_usuario(uow: UsuariosUnitOfWork, usuario_id: int) -> list[AsignacionRol]:
    """Lista las asignaciones de rol históricas y vigentes de un usuario."""
    usuario = await uow.usuarios.get_by_id(usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado.")
    return await uow.asignaciones_rol.get_by_usuario(usuario_id)


async def asignar_rol(
    uow: UsuariosUnitOfWork, admin_actual: Usuario, usuario_id: int, datos: AsignarRolIn
) -> AsignacionRol:
    """Asignación de un rol con vigencia (RN-03, RN-16 y Ejercicio 5).

    Si ya existía una asignación abierta vencida, se cierra y se abre la nueva fila.
    Si ya existía una asignación abierta vigente, se rechaza con 409 Conflicto.
    """
    ahora = datetime.now(UTC)
    try:
        async with uow:
            usuario = await uow.usuarios.get_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("Usuario no encontrado.")

            abierta = await uow.asignaciones_rol.get_abierta_por_usuario_y_rol(
                usuario_id, datos.rol
            )
            if abierta is not None:
                if abierta.vence_en is not None and abierta.vence_en <= ahora:
                    # Cerrar asignación anterior vencida
                    await uow.asignaciones_rol.update(abierta, {"revocada_en": ahora})
                else:
                    raise Conflicto(
                        f"El usuario ya tiene el rol {datos.rol} asignado y vigente."
                    )

            nueva = AsignacionRol(
                usuario_id=usuario_id,
                rol=datos.rol,
                desde=ahora,
                vence_en=datos.vence_en,
                otorgada_por=admin_actual.id,
            )
            await uow.asignaciones_rol.add(nueva)

            evento = EventoSeguridad(
                actor=admin_actual.email,
                accion=f"Asignación de rol {datos.rol} a {usuario.email}",
            )
            await uow.eventos_seguridad.add(evento)
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, _MAPA_RESTRICCIONES_USUARIOS) from exc

    return nueva


async def revocar_rol(
    uow: UsuariosUnitOfWork, admin_actual: Usuario, usuario_id: int, rol: str
) -> AsignacionRol:
    """Revocación de un rol vigente (RN-05, RN-16)."""
    if rol not in ROLES_SISTEMA:
        raise NoEncontrado("El rol indicado no existe o no está asignado.")

    ahora = datetime.now(UTC)
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise NoEncontrado("Usuario no encontrado.")

        abierta = await uow.asignaciones_rol.get_abierta_por_usuario_y_rol(usuario_id, rol)
        if abierta is None or (abierta.vence_en is not None and abierta.vence_en <= ahora):
            raise NoEncontrado(f"El usuario no tiene una asignación vigente del rol {rol}.")

        # RN-05: Autoprotección de administradores
        if rol == "ADMIN":
            if usuario_id == admin_actual.id:
                raise Conflicto("Un administrador no puede revocarse su propio rol ADMIN.")
            otros_admins = await uow.asignaciones_rol.contar_admins_vigentes(
                ahora=ahora, excluir_usuario_id=usuario_id
            )
            if otros_admins < 1:
                raise Conflicto("El sistema no puede quedar sin administradores vigentes.")

        await uow.asignaciones_rol.update(abierta, {"revocada_en": ahora})

        evento = EventoSeguridad(
            actor=admin_actual.email,
            accion=f"Revocación de rol {rol} a {usuario.email}",
        )
        await uow.eventos_seguridad.add(evento)

    return abierta


# --- Auditoría de Seguridad (/eventos) ---


async def listar_eventos(
    uow: UsuariosUnitOfWork, page: int, size: int
) -> Pagina[EventoSeguridadOut]:
    """Listado paginado de eventos de seguridad (GET /eventos)."""
    total = await uow.eventos_seguridad.count()
    _, offset = calcular_paginas(total=total, page=page, size=size)
    items = await uow.eventos_seguridad.listar_paginado(offset=offset, limit=size)
    return armar_pagina(
        items=[EventoSeguridadOut.model_validate(e) for e in items],
        total=total,
        page=page,
        size=size,
    )
