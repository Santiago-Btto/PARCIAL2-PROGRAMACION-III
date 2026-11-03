from sqlalchemy.exc import IntegrityError

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.libros.models import Libro


ERRORES: MapaRestricciones = {
    "uq_editorial_nombre": (Conflicto, "Ya existe una editorial con ese nombre."),
}


async def _obtener(uow: EditorialesUnitOfWork, editorial_id: int) -> Editorial:
    entidad = await uow.editoriales.get_by_id(editorial_id)
    if entidad is None:
        raise NoEncontrado("La editorial no existe.")
    return entidad


async def crear(uow: EditorialesUnitOfWork, datos: EditorialCreate) -> Editorial:
    try:
        async with uow:
            entidad = await uow.editoriales.add(Editorial.model_validate(datos))
        return entidad
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def listar(uow: EditorialesUnitOfWork, page: int, size: int) -> Pagina[Editorial]:
    async with uow:
        total = await uow.editoriales.count()
        _, offset = calcular_paginas(total, page, size)
        items = await uow.editoriales.get_all(offset=offset, limit=size)
        return armar_pagina(items, total, page, size)


async def obtener(uow: EditorialesUnitOfWork, editorial_id: int) -> Editorial:
    async with uow:
        return await _obtener(uow, editorial_id)


async def actualizar(
    uow: EditorialesUnitOfWork, editorial_id: int, datos: EditorialUpdate
) -> Editorial:
    try:
        async with uow:
            entidad = await _obtener(uow, editorial_id)
            return await uow.editoriales.update(entidad, datos.model_dump(exclude_unset=True))
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def listar_libros(
    uow: EditorialesUnitOfWork, editorial_id: int, page: int, size: int
) -> Pagina[Libro]:
    async with uow:
        await _obtener(uow, editorial_id)
        return await uow.libros.listar_pagina(page=page, size=size, editorial_id=editorial_id)
