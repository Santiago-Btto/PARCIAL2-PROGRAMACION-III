from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.models import Libro
from app.modules.libros.service import consulta_listado

ERRORES: MapaRestricciones = {
    "uq_genero_nombre": (Conflicto, "Ya existe un género con ese nombre."),
}


async def crear(session: AsyncSession, datos: GeneroCreate) -> Genero:
    genero = Genero.model_validate(datos)
    session.add(genero)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return genero


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Genero]:
    consulta = select(Genero).order_by(col(Genero.id)).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())


async def listar_libros(session: AsyncSession, genero_id: int, limit: int, offset: int) -> list[Libro]:
    if await session.get(Genero, genero_id) is None:
        raise NoEncontrado("El género no existe.")
    consulta = consulta_listado().where(Libro.genero_id == genero_id).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())
