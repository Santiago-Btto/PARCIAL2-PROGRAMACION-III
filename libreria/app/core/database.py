"""Motor, fábrica de sesiones y dependencia get_session.

El motor y la fábrica NO se crean al importar este módulo: los crea el lifespan
de la aplicación (app/main.py) y los guarda en app.state.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings

# Convención de nombres para índices y restricciones. Tiene dos usos:
#  1. Alembic genera nombres estables (y puede borrar las FK en el downgrade).
#  2. El service traduce un IntegrityError a un mensaje propio mirando el nombre
#     de la restricción que falló, sin mostrar nunca el texto de la base (RN-12).
# Debe aplicarse antes de declarar cualquier tabla: cada models.py importa este módulo.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = NAMING_CONVENTION


def crear_motor(echo: bool | None = None) -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.sql_echo if echo is None else echo,
        pool_pre_ping=True,
    )


def crear_fabrica_sesiones(motor: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: después del commit los atributos siguen disponibles
    # sin disparar una recarga implícita (que en async no está permitida).
    return async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una sesión por petición, tomada de la fábrica creada en el lifespan."""
    fabrica: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with fabrica() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
