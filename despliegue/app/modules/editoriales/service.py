from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.libros.models import Libro
from app.modules.libros.service import consulta_listado

ERRORES: MapaRestricciones = {
    "uq_editorial_nombre": (Conflicto, "Ya existe una editorial con ese nombre."),
}


async def crear(session: AsyncSession, datos: EditorialCreate) -> Editorial:
    editorial = Editorial.model_validate(datos)
    session.add(editorial)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return editorial


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Editorial]:
    consulta = select(Editorial).order_by(col(Editorial.id)).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())


async def obtener(session: AsyncSession, editorial_id: int) -> Editorial:
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise NoEncontrado("La editorial no existe.")
    return editorial


async def actualizar(session: AsyncSession, editorial_id: int, datos: EditorialUpdate) -> Editorial:
    editorial = await obtener(session, editorial_id)
    editorial.sqlmodel_update(datos.model_dump(exclude_unset=True))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return editorial


async def listar_libros(
    session: AsyncSession, editorial_id: int, limit: int, offset: int
) -> list[Libro]:
    await obtener(session, editorial_id)  # 404 si la editorial no existe
    consulta = consulta_listado().where(Libro.editorial_id == editorial_id).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())
