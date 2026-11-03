"""Reglas del catálogo de libros y operaciones transaccionales de stock."""

from sqlalchemy.exc import IntegrityError

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.core.paginacion import Pagina
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.repository import LibroRepository
from app.modules.libros.schemas import LibroCreate, LibroUpdate, ReposicionCreate
from app.modules.libros.stock import cambiar_stock
from app.modules.libros.unit_of_work import LibrosUnitOfWork

ERRORES: MapaRestricciones = {
    "uq_libro_isbn": (Conflicto, "Ya existe un libro con ese ISBN."),
    "uq_libro_isbn_vigente": (Conflicto, "Ya existe un libro vigente con ese ISBN."),
    "fk_libro_editorial_id_editorial": (Conflicto, "La editorial indicada no existe."),
    "fk_libro_genero_id_genero": (Conflicto, "El género indicado no existe."),
    "fk_libro_autor_autor_id_autor": (Conflicto, "Alguno de los autores indicados no existe."),
    "fk_movimiento_stock_usuario_id_usuario": (Conflicto, "El usuario que registra el movimiento no existe."),
    "pk_libro_autor": (Conflicto, "Un mismo autor no puede figurar dos veces en el libro."),
    "ck_libro_precio_positivo": (Conflicto, "El precio debe ser mayor que cero."),
    "ck_libro_stock_no_negativo": (Conflicto, "El stock no puede ser negativo."),
    "ck_libro_autor_orden_positivo": (Conflicto, "El orden de cada autoría empieza en 1."),
    "ck_libro_autor_rol_valido": (Conflicto, "El rol de la autoría no es válido."),
}


async def listar(
    uow: LibrosUnitOfWork, *, page: int, size: int,
    titulo: str | None = None, genero_id: int | None = None,
) -> Pagina:
    return await uow.libros.listar_pagina(page=page, size=size, titulo=titulo, genero_id=genero_id)


async def obtener_detalle(uow: LibrosUnitOfWork, libro_id: int):
    libro = await uow.libros.obtener_detalle(libro_id)
    if libro is None:
        raise NoEncontrado("El libro no existe.")
    return libro


async def crear(uow: LibrosUnitOfWork, datos: LibroCreate, *, usuario_id: int):
    libro_id: int
    try:
        async with uow:
            libro = Libro(
                **datos.model_dump(exclude={"autores", "stock_inicial"}),
                stock=0,
                autorias=[
                    LibroAutor(autor_id=autoria.autor_id, rol=autoria.rol, orden=autoria.orden)
                    for autoria in datos.autores
                ],
            )
            libro = await uow.libros.add(libro)
            libro_id = libro.id
            if datos.stock_inicial:
                await cambiar_stock(
                    uow,
                    libro_id=libro_id,
                    cantidad=datos.stock_inicial,
                    usuario_id=usuario_id,
                    motivo="Stock inicial",
                )
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener_detalle(uow, libro_id)


async def actualizar(uow: LibrosUnitOfWork, libro_id: int, datos: LibroUpdate):
    try:
        async with uow:
            libro = await uow.libros.get_for_update(libro_id)
            if libro is None or libro.borrado_en is not None:
                raise NoEncontrado("El libro no existe.")
            await uow.libros.update(libro, datos.model_dump(exclude_unset=True))
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener_detalle(uow, libro_id)


async def reponer(
    uow: LibrosUnitOfWork, libro_id: int, datos: ReposicionCreate, *, usuario_id: int
):
    try:
        async with uow:
            await cambiar_stock(
                uow, libro_id=libro_id, cantidad=datos.cantidad,
                usuario_id=usuario_id, motivo=datos.motivo,
            )
    except IntegrityError as exc:
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener_detalle(uow, libro_id)


async def eliminar(uow: LibrosUnitOfWork, libro_id: int) -> None:
    async with uow:
        libro = await uow.libros.get_for_update(libro_id)
        if libro is None or libro.borrado_en is not None:
            raise NoEncontrado("El libro no existe.")
        await uow.libros.soft_delete(libro)


async def listar_movimientos(
    uow: LibrosUnitOfWork, libro_id: int, *, page: int, size: int
) -> Pagina:
    if await uow.libros.get_by_id_including_deleted(libro_id) is None:
        raise NoEncontrado("El libro no existe.")
    return await uow.movimientos.listar_pagina_por_libro(libro_id, page=page, size=size)
