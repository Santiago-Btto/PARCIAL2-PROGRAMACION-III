from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.ventas.repository import VentaRepository


class VentasUnitOfWork(UnitOfWork):
    """Compone todo lo que toca el registro de una venta (RN-10) sobre UNA sesión:
    la venta y sus renglones, el cliente, el stock de cada libro y sus movimientos.

    Expone `libros` y `movimientos` con los nombres que pide `cambiar_stock`, así
    el descuento usa el mismo punto único de escritura de stock que el catálogo.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.ventas = VentaRepository(session)
        self.clientes = ClienteRepository(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)


def get_ventas_uow(session: SessionDep) -> VentasUnitOfWork:
    return VentasUnitOfWork(session)


VentasUowDep = Annotated[VentasUnitOfWork, Depends(get_ventas_uow)]
