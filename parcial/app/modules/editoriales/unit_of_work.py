from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.repository import EditorialRepository
from app.modules.libros.repository import LibroRepository


class EditorialesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.editoriales = EditorialRepository(session)
        self.libros = LibroRepository(session)


def get_editoriales_uow(session: SessionDep) -> EditorialesUnitOfWork:
    return EditorialesUnitOfWork(session)


EditorialesUowDep = Annotated[EditorialesUnitOfWork, Depends(get_editoriales_uow)]
