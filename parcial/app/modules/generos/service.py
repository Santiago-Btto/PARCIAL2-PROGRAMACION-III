from sqlalchemy.exc import IntegrityError

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.generos.unit_of_work import GenerosUnitOfWork
from app.modules.libros.models import Libro


ERRORES: MapaRestricciones = {
    "uq_genero_nombre": (Conflicto, "Ya existe un género con ese nombre."),
}


async def _obtener(uow: GenerosUnitOfWork, genero_id: int) -> Genero:
    entidad = await uow.generos.get_by_id(genero_id)
    if entidad is None:
        raise NoEncontrado("El género no existe.")
    return entidad


async def crear(uow: GenerosUnitOfWork, datos: GeneroCreate) -> Genero:
    try:
        async with uow:
            entidad = await uow.generos.add(Genero.model_validate(datos))
        return entidad
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None


async def listar(uow: GenerosUnitOfWork, page: int, size: int) -> Pagina[Genero]:
    async with uow:
        total = await uow.generos.count()
        _, offset = calcular_paginas(total, page, size)
        items = await uow.generos.get_all(offset=offset, limit=size)
        return armar_pagina(items, total, page, size)


async def obtener(uow: GenerosUnitOfWork, genero_id: int) -> Genero:
    async with uow:
        return await _obtener(uow, genero_id)


async def listar_libros(
    uow: GenerosUnitOfWork, genero_id: int, page: int, size: int
) -> Pagina[Libro]:
    async with uow:
        await _obtener(uow, genero_id)
        return await uow.libros.listar_pagina(page=page, size=size, genero_id=genero_id)
