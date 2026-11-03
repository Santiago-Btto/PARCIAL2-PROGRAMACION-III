from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository


class LibrosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)


def get_libros_uow(session: SessionDep) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


LibrosUowDep = Annotated[LibrosUnitOfWork, Depends(get_libros_uow)]
