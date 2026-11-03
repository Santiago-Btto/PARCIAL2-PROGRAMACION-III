"""Único punto de variación de stock del catálogo, reutilizable por ventas.

El llamador abre su UoW y conserva la responsabilidad de confirmar o revertir.
"""

from typing import TYPE_CHECKING, Protocol

from app.core.errores import Conflicto, DatosInvalidos, NoEncontrado
from app.core.parametros import MAX_ID
from app.modules.libros.models import Libro, MovimientoStock

if TYPE_CHECKING:
    from app.modules.libros.repository import LibroRepository, MovimientoStockRepository

    class UnidadCambioStock(Protocol):
        libros: LibroRepository
        movimientos: MovimientoStockRepository


async def cambiar_stock(
    uow: "UnidadCambioStock", *, libro_id: int, cantidad: int,
    usuario_id: int, motivo: str, venta_id: int | None = None,
) -> Libro:
    if cantidad == 0 or not motivo.strip() or len(motivo) > 200:
        raise DatosInvalidos("La variación debe ser no nula y tener un motivo válido.")
    libro = await uow.libros.get_for_update(libro_id)
    if libro is None:
        raise NoEncontrado("El libro no existe.")
    if libro.borrado_en is not None:
        raise Conflicto("El libro está dado de baja.")
    nuevo_stock = libro.stock + cantidad
    if not 0 <= nuevo_stock <= MAX_ID:
        raise Conflicto("El stock resultante está fuera del rango permitido.")

    libro.stock = nuevo_stock
    await uow.libros.update(libro)
    await uow.movimientos.add(MovimientoStock(
        libro_id=libro_id, venta_id=venta_id, usuario_id=usuario_id,
        cantidad=cantidad, motivo=motivo,
    ))
    return libro
