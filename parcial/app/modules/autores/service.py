from sqlalchemy.orm import joinedload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import NoEncontrado
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate, LibroDeAutor
from app.modules.libros.models import LibroAutor


async def crear(session: AsyncSession, datos: AutorCreate) -> Autor:
    autor = Autor.model_validate(datos)
    session.add(autor)
    await session.commit()
    return autor


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Autor]:
    consulta = select(Autor).order_by(col(Autor.id)).limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())


async def obtener(session: AsyncSession, autor_id: int) -> Autor:
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise NoEncontrado("El autor no existe.")
    return autor


async def actualizar(session: AsyncSession, autor_id: int, datos: AutorUpdate) -> Autor:
    autor = await obtener(session, autor_id)
    autor.sqlmodel_update(datos.model_dump(exclude_unset=True))
    await session.commit()
    return autor


async def listar_libros(
    session: AsyncSession, autor_id: int, limit: int, offset: int
) -> list[LibroDeAutor]:
    await obtener(session, autor_id)
    # Una sola consulta: autorías del autor + su libro (relación a uno -> joinedload).
    consulta = (
        select(LibroAutor)
        .where(LibroAutor.autor_id == autor_id)
        .options(joinedload(LibroAutor.libro))  # type: ignore[arg-type]
        .order_by(col(LibroAutor.libro_id))
        .limit(limit)
        .offset(offset)
    )
    autorias = (await session.exec(consulta)).all()
    return [
        LibroDeAutor(
            libro_id=a.libro_id,
            isbn=a.libro.isbn,
            titulo=a.libro.titulo,
            precio=a.libro.precio,
            rol=a.rol,
            orden=a.orden,
        )
        for a in autorias
        if a.libro is not None
    ]
