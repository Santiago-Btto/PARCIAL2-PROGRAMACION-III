from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.generos.repository import GeneroRepository
from app.modules.libros.repository import LibroRepository


class GenerosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.generos = GeneroRepository(session)
        self.libros = LibroRepository(session)


def get_generos_uow(session: SessionDep) -> GenerosUnitOfWork:
    return GenerosUnitOfWork(session)


GenerosUowDep = Annotated[GenerosUnitOfWork, Depends(get_generos_uow)]
