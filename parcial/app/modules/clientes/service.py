from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate
from app.modules.ventas.models import Venta
from app.modules.ventas.service import consulta_listado

ERRORES: MapaRestricciones = {
    "uq_cliente_email": (Conflicto, "Ya existe un cliente con ese email."),
    # RN-09: el índice UNIQUE de perfil_cliente.cliente_id rechaza el segundo perfil.
    "ix_perfil_cliente_cliente_id": (Conflicto, "El cliente ya tiene un perfil."),
    # El perfil se escribe sin consultar antes al cliente: si la FK falla, el cliente no existe.
    "fk_perfil_cliente_cliente_id_cliente": (NoEncontrado, "El cliente no existe."),
}


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def obtener(session: AsyncSession, cliente_id: int) -> Cliente:
    """Cliente con su perfil (relación a uno -> joinedload): una sola consulta."""
    consulta = (
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))  # type: ignore[arg-type]
        .execution_options(populate_existing=True)
    )
    cliente = (await session.exec(consulta)).first()
    if cliente is None:
        raise NoEncontrado("El cliente no existe.")
    return cliente


async def crear(session: AsyncSession, datos: ClienteCreate) -> Cliente:
    cliente = Cliente.model_validate(datos)
    session.add(cliente)
    await _commit(session)  # RN-02: la unicidad la garantiza la base, sin consulta previa
    return await obtener(session, cliente.id)  # type: ignore[arg-type]


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Cliente]:
    consulta = (
        select(Cliente)
        .options(joinedload(Cliente.perfil))  # type: ignore[arg-type]
        .order_by(col(Cliente.id))
        .limit(limit)
        .offset(offset)
    )
    return list((await session.exec(consulta)).all())


async def actualizar(session: AsyncSession, cliente_id: int, datos: ClienteUpdate) -> Cliente:
    cliente = await obtener(session, cliente_id)
    cliente.sqlmodel_update(datos.model_dump(exclude_unset=True))
    await _commit(session)
    return await obtener(session, cliente_id)


async def crear_perfil(session: AsyncSession, cliente_id: int, datos: PerfilCreate) -> PerfilCliente:
    perfil = PerfilCliente(cliente_id=cliente_id, **datos.model_dump())
    session.add(perfil)
    await _commit(session)
    return perfil


async def listar_ventas(
    session: AsyncSession, cliente_id: int, limit: int, offset: int
) -> list[Venta]:
    if await session.get(Cliente, cliente_id) is None:
        raise NoEncontrado("El cliente no existe.")
    consulta = consulta_listado().where(Venta.cliente_id == cliente_id).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())
