"""Repositorios de clientes y perfiles; ninguna operación confirma la sesión."""

from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Cliente)

    async def obtener_con_perfil(self, cliente_id: int) -> Cliente | None:
        """Cliente con su perfil (relación a uno -> joinedload): una sola consulta."""
        consulta = (
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(joinedload(Cliente.perfil))  # type: ignore[arg-type]
            .execution_options(populate_existing=True)
        )
        return (await self.session.exec(consulta)).first()

    async def obtener_por_usuario(self, usuario_id: int) -> Cliente | None:
        """Ficha de cliente vinculada a una cuenta web (cliente.usuario_id es UNIQUE)."""
        consulta = select(Cliente).where(Cliente.usuario_id == usuario_id)
        return (await self.session.exec(consulta)).first()

    async def listar_pagina(self, *, page: int, size: int) -> Pagina[Cliente]:
        total = await self.count()
        _, offset = calcular_paginas(total, page, size)
        clientes = await self.get_all(
            offset=offset, limit=size, options=(joinedload(Cliente.perfil),)  # type: ignore[arg-type]
        )
        return armar_pagina(clientes, total, page, size)


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PerfilCliente)
