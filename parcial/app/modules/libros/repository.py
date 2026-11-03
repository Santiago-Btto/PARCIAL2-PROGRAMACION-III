"""Consultas de catálogo e historial; ninguna operación confirma la sesión."""

from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.paginacion import Pagina, armar_pagina, calcular_paginas
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock

OPCIONES_LISTADO = (joinedload(Libro.editorial), joinedload(Libro.genero))


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class LibroRepository(SoftDeleteRepository[Libro]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Libro)

    async def get_for_update(self, libro_id: int) -> Libro | None:
        consulta = (
            select(Libro)
            .where(Libro.id == libro_id)
            .with_for_update(of=Libro)
            .execution_options(populate_existing=True)
        )
        return (await self.session.exec(consulta)).first()

    async def obtener_detalle(self, libro_id: int) -> Libro | None:
        consulta = (
            select(Libro)
            .where(Libro.id == libro_id, col(Libro.borrado_en).is_(None))
            .options(*OPCIONES_LISTADO, selectinload(Libro.autorias).joinedload(LibroAutor.autor))
            .execution_options(populate_existing=True)
        )
        return (await self.session.exec(consulta)).first()

    async def listar_pagina(
        self, *, page: int, size: int, titulo: str | None = None,
        genero_id: int | None = None, editorial_id: int | None = None,
    ) -> Pagina[Libro]:
        filtros = []
        if titulo:
            filtros.append(col(Libro.titulo).ilike(f"%{_escapar_like(titulo)}%", escape="\\"))
        if genero_id is not None:
            filtros.append(Libro.genero_id == genero_id)
        if editorial_id is not None:
            filtros.append(Libro.editorial_id == editorial_id)
        total = await self.count(filters=filtros)
        _, offset = calcular_paginas(total, page, size)
        libros = await self.get_all(offset=offset, limit=size, filters=filtros, options=OPCIONES_LISTADO)
        return armar_pagina(libros, total, page, size)

    async def listar_autorias(self, autor_id: int, *, page: int, size: int) -> Pagina[LibroAutor]:
        filtros = (LibroAutor.autor_id == autor_id, col(Libro.borrado_en).is_(None))
        total = int(await self.session.scalar(
            select(func.count()).select_from(LibroAutor).join(Libro).where(*filtros)
        ) or 0)
        _, offset = calcular_paginas(total, page, size)
        consulta = (
            select(LibroAutor).join(Libro).where(*filtros)
            .options(joinedload(LibroAutor.libro))
            .order_by(LibroAutor.libro_id).offset(offset).limit(size)
        )
        return armar_pagina(list((await self.session.exec(consulta)).all()), total, page, size)


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MovimientoStock)

    async def listar_pagina_por_libro(
        self, libro_id: int, *, page: int, size: int
    ) -> Pagina[MovimientoStock]:
        filtros = (MovimientoStock.libro_id == libro_id,)
        total = await self.count(filters=filtros)
        _, offset = calcular_paginas(total, page, size)
        movimientos = await self.get_all(
            filters=filtros,
            offset=offset,
            limit=size,
            order_by=MovimientoStock.id,
        )
        return armar_pagina(movimientos, total, page, size)
