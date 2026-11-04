from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository
from app.modules.ventas.repository import VentaRepository


class ClientesUnitOfWork(UnitOfWork):
    """Clientes, perfiles y las ventas de cada cliente sobre la sesión de la petición."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.perfiles = PerfilClienteRepository(session)
        self.ventas = VentaRepository(session)


def get_clientes_uow(session: SessionDep) -> ClientesUnitOfWork:
    return ClientesUnitOfWork(session)


ClientesUowDep = Annotated[ClientesUnitOfWork, Depends(get_clientes_uow)]
