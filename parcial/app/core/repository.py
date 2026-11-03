"""Jerarquía base de repositorios (Ejercicio 6).

- BaseRepository[T] recibe en su constructor la sesión y la clase del modelo
  (porque los genéricos de Python se borran en tiempo de ejecución).
- Ofrece get_by_id, get_all, count, add, update y delete.
- add y update hacen flush(), NUNCA commit(): ningún repositorio confirma.
- SoftDeleteRepository[T] hereda de BaseRepository[T], filtra los registros con
  borrado_en IS NOT NULL en sus lecturas habituales y agrega
  get_by_id_including_deleted y soft_delete (que no existen en la clase base).
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, entity_id: int, *, options: Sequence[Any] = ()) -> T | None:
        stmt = select(self.model_cls).where(getattr(self.model_cls, "id") == entity_id)
        if options:
            stmt = stmt.options(*options)
        resultado = await self.session.exec(stmt)
        return resultado.first()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        filters: Sequence[ColumnElement[bool]] = (),
        order_by: Any = None,
        options: Sequence[Any] = (),
    ) -> list[T]:
        stmt = select(self.model_cls)
        for cond in filters:
            stmt = stmt.where(cond)
        if options:
            stmt = stmt.options(*options)
        if order_by is not None:
            if isinstance(order_by, (list, tuple)):
                stmt = stmt.order_by(*order_by)
            else:
                stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(getattr(self.model_cls, "id"))
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        resultado = await self.session.exec(stmt)
        return list(resultado.all())

    async def count(self, *, filters: Sequence[ColumnElement[bool]] = ()) -> int:
        stmt = select(func.count()).select_from(self.model_cls)
        for cond in filters:
            stmt = stmt.where(cond)
        total = await self.session.scalar(stmt)
        return int(total or 0)

    async def add(self, entity: T) -> T:
        """Agrega la entidad y hace flush() para obtener su id y validar restricciones.
        Nunca hace commit(): la confirmación pertenece al Unit of Work.
        """
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T, cambios: dict[str, Any] | None = None) -> T:
        """Actualiza los campos indicados sobre la entidad y ejecuta flush(), nunca commit()."""
        if cambios:
            for campo, valor in cambios.items():
                setattr(entity, campo, valor)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        """Elimina físicamente la entidad de la base y ejecuta flush(), nunca commit()."""
        await self.session.delete(entity)
        await self.session.flush()


class SoftDeleteRepository(BaseRepository[T], Generic[T]):
    """Repositorio para entidades con borrado lógico (columna borrado_en).

    Filtra las filas dadas de baja en get_by_id, get_all y count, y agrega
    get_by_id_including_deleted y soft_delete.
    """

    def _condicion_vigente(self) -> ColumnElement[bool]:
        columna_borrado = getattr(self.model_cls, "borrado_en")
        return columna_borrado.is_(None)

    async def get_by_id(self, entity_id: int, *, options: Sequence[Any] = ()) -> T | None:
        stmt = (
            select(self.model_cls)
            .where(getattr(self.model_cls, "id") == entity_id)
            .where(self._condicion_vigente())
        )
        if options:
            stmt = stmt.options(*options)
        resultado = await self.session.exec(stmt)
        return resultado.first()

    async def get_by_id_including_deleted(
        self, entity_id: int, *, options: Sequence[Any] = ()
    ) -> T | None:
        stmt = select(self.model_cls).where(getattr(self.model_cls, "id") == entity_id)
        if options:
            stmt = stmt.options(*options)
        resultado = await self.session.exec(stmt)
        return resultado.first()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        filters: Sequence[ColumnElement[bool]] = (),
        order_by: Any = None,
        options: Sequence[Any] = (),
    ) -> list[T]:
        filtros_vigentes = [self._condicion_vigente(), *filters]
        return await super().get_all(
            offset=offset,
            limit=limit,
            filters=filtros_vigentes,
            order_by=order_by,
            options=options,
        )

    async def count(self, *, filters: Sequence[ColumnElement[bool]] = ()) -> int:
        filtros_vigentes = [self._condicion_vigente(), *filters]
        return await super().count(filters=filtros_vigentes)

    async def soft_delete(self, entity: T) -> T:
        """Marca la entidad como dada de baja escribiendo borrado_en y hace flush()."""
        setattr(entity, "borrado_en", datetime.now(UTC))
        self.session.add(entity)
        await self.session.flush()
        return entity
