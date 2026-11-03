from sqlalchemy.exc import IntegrityError

from app.core.errores import MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate, LibroDeAutor
from app.modules.autores.unit_of_work import AutoresUnitOfWork


ERRORES: MapaRestricciones = {}


async def _obtener(uow: AutoresUnitOfWork, autor_id: int) -> Autor:
    entidad = await uow.autores.get_by_id(autor_id)
    if entidad is None:
        raise NoEncontrado("El autor no existe.")
    return entidad


async def crear(uow: AutoresUnitOfWork, datos: AutorCreate) -> Autor:
    try:
        async with uow:
            entidad = await uow.autores.add(Autor.model_validate(datos))
        return entidad
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def listar(uow: AutoresUnitOfWork, page: int, size: int) -> Pagina[Autor]:
    async with uow:
        total = await uow.autores.count()
        _, offset = calcular_paginas(total, page, size)
        items = await uow.autores.get_all(offset=offset, limit=size)
        return armar_pagina(items, total, page, size)


async def obtener(uow: AutoresUnitOfWork, autor_id: int) -> Autor:
    async with uow:
        return await _obtener(uow, autor_id)


async def actualizar(
    uow: AutoresUnitOfWork, autor_id: int, datos: AutorUpdate
) -> Autor:
    try:
        async with uow:
            entidad = await _obtener(uow, autor_id)
            return await uow.autores.update(entidad, datos.model_dump(exclude_unset=True))
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def listar_libros(
    uow: AutoresUnitOfWork, autor_id: int, page: int, size: int
) -> Pagina[LibroDeAutor]:
    async with uow:
        await _obtener(uow, autor_id)
        pagina = await uow.libros.listar_autorias(autor_id, page=page, size=size)
        items = [
            LibroDeAutor(
                libro_id=autoria.libro_id,
                isbn=autoria.libro.isbn,
                titulo=autoria.libro.titulo,
                precio=autoria.libro.precio,
                rol=autoria.rol,
                orden=autoria.orden,
            )
            for autoria in pagina.items
        ]
        return armar_pagina(items, pagina.total, page, size)
