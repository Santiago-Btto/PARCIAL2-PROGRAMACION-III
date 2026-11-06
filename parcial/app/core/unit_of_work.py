"""Unit of Work base (Ejercicio 6).

Es un gestor de contexto asincrónico:
- Recibe la AsyncSession de la petición (la misma que usan las dependencias de auth).
- Al salir normalmente del bloque `async with`, confirma la transacción (`commit()`).
- Si se sale con una excepción (o si falla el `commit()`), revierte la transacción (`rollback()`).
- NO cierra la sesión (`close()`), porque no la creó: la creó `get_session`.
"""

from types import TracebackType
from typing import Self

from sqlmodel.ext.asyncio.session import AsyncSession


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            try:
                await self.commit()
            except Exception:
                await self.rollback()
                raise

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
