"""Reglas de clientes y perfiles (Ejercicio 6).

El service recibe el Unit of Work ya construido por el router y lo abre con
`async with`; nunca lo construye ni confirma por su cuenta. La unicidad del
correo y del perfil la garantiza la base: no hay consultas previas.
"""

from sqlalchemy.exc import IntegrityError

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.core.paginacion import Pagina
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.models import Venta

ERRORES: MapaRestricciones = {
    "uq_cliente_email": (Conflicto, "Ya existe un cliente con ese email."),
    # El índice UNIQUE de perfil_cliente.cliente_id rechaza el segundo perfil.
    "ix_perfil_cliente_cliente_id": (Conflicto, "El cliente ya tiene un perfil."),
    # El perfil se escribe sin consultar antes al cliente: si la FK falla, el cliente no existe.
    "fk_perfil_cliente_cliente_id_cliente": (NoEncontrado, "El cliente no existe."),
}


async def _detalle(uow: ClientesUnitOfWork, cliente_id: int) -> Cliente:
    cliente = await uow.clientes.obtener_con_perfil(cliente_id)
    if cliente is None:
        raise NoEncontrado("El cliente no existe.")
    return cliente


async def crear(uow: ClientesUnitOfWork, datos: ClienteCreate) -> Cliente:
    try:
        async with uow:
            cliente = await uow.clientes.add(Cliente.model_validate(datos))
            cliente_id = cliente.id
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener(uow, cliente_id)  # type: ignore[arg-type]


async def listar(uow: ClientesUnitOfWork, *, page: int, size: int) -> Pagina[Cliente]:
    async with uow:
        return await uow.clientes.listar_pagina(page=page, size=size)


async def obtener(uow: ClientesUnitOfWork, cliente_id: int) -> Cliente:
    async with uow:
        return await _detalle(uow, cliente_id)


async def actualizar(uow: ClientesUnitOfWork, cliente_id: int, datos: ClienteUpdate) -> Cliente:
    try:
        async with uow:
            cliente = await uow.clientes.get_by_id(cliente_id)
            if cliente is None:
                raise NoEncontrado("El cliente no existe.")
            await uow.clientes.update(cliente, datos.model_dump(exclude_unset=True))
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener(uow, cliente_id)


async def crear_perfil(
    uow: ClientesUnitOfWork, cliente_id: int, datos: PerfilCreate
) -> PerfilCliente:
    try:
        async with uow:
            perfil = await uow.perfiles.add(PerfilCliente(cliente_id=cliente_id, **datos.model_dump()))
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return perfil


async def listar_ventas(
    uow: ClientesUnitOfWork, cliente_id: int, *, page: int, size: int
) -> Pagina[Venta]:
    async with uow:
        if await uow.clientes.get_by_id(cliente_id) is None:
            raise NoEncontrado("El cliente no existe.")
        return await uow.ventas.listar_pagina(page=page, size=size, cliente_id=cliente_id)
