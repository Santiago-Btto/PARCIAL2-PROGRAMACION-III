"""Repositorio de ventas; ninguna operación confirma la sesión."""

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.core.repository import BaseRepository
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Venta)

    async def obtener_detalle(self, venta_id: int) -> Venta | None:
        """Venta con cliente, renglones y el libro de cada renglón en un número FIJO
        de consultas (2), que no crece con la cantidad de renglones (caso C-15):

        1. venta JOIN cliente                                (joinedload, a uno)
        2. renglon_venta JOIN libro WHERE venta_id IN (...)  (selectinload de la
                                                              colección + joinedload)

        El libro se carga por la relación del renglón, sin el filtro de vigencia del
        SoftDeleteRepository: una venta vieja sigue mostrando un libro dado de baja.
        """
        consulta = (
            select(Venta)
            .where(Venta.id == venta_id)
            .options(
                joinedload(Venta.cliente),  # type: ignore[arg-type]
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),  # type: ignore[arg-type]
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.exec(consulta)).first()

    async def listar_pagina(
        self, *, page: int, size: int, cliente_id: int | None = None
    ) -> Pagina[Venta]:
        """Ventas con su cliente; total y página usan los mismos filtros."""
        filtros = [Venta.cliente_id == cliente_id] if cliente_id is not None else []
        total = await self.count(filters=filtros)
        _, offset = calcular_paginas(total, page, size)
        ventas = await self.get_all(
            offset=offset,
            limit=size,
            filters=filtros,
            options=(joinedload(Venta.cliente),),  # type: ignore[arg-type]
        )
        return armar_pagina(ventas, total, page, size)
