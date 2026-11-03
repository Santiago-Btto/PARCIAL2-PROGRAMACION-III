from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository
from app.modules.libros.repository import LibroRepository


class AutoresUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.autores = AutorRepository(session)
        self.libros = LibroRepository(session)


def get_autores_uow(session: SessionDep) -> AutoresUnitOfWork:
    return AutoresUnitOfWork(session)


AutoresUowDep = Annotated[AutoresUnitOfWork, Depends(get_autores_uow)]
