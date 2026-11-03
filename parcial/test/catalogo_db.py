"""Fixtures PostgreSQL opt-in, exclusivamente sobre un destino sintético local.

El esquema debe estar migrado con Alembic antes de ejecutar estos tests.
No se usa create_all ni el seed de la aplicación.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.core.modelos  # noqa: F401


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def database_url():
    valor = os.environ.get("CATALOGO_TEST_DATABASE_URL")
    if not valor:
        pytest.skip("Definir CATALOGO_TEST_DATABASE_URL para PostgreSQL aislado")
    url = make_url(valor)
    if (url.drivername != "postgresql+asyncpg" or url.host not in {"127.0.0.1", "localhost", "::1"}
            or not url.database or not url.database.endswith("_test")):
        pytest.fail("Destino rechazado: se requiere PostgreSQL loopback y base *_test")
    return valor


@pytest.fixture
async def db_factory(database_url, monkeypatch):
    # conftest legado cambia este alias globalmente; aquí usamos su implementación real.
    monkeypatch.setattr(asyncio, "to_thread", asyncio.threads.to_thread)
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        version = int(await connection.scalar(text("SHOW server_version_num")))
        assert 160000 <= version < 170000, "La evidencia C-03 requiere PostgreSQL 16"
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == "c8e31f5a9021", "Ejecutar las cuatro migraciones Alembic"
        # TRUNCATE no dispara el trigger de UPDATE/DELETE. Sólo se permite en la base
        # sintética validada arriba; deja independientes también los tests concurrentes.
        await connection.execute(text(
            "TRUNCATE movimiento_stock, renglon_venta, venta, perfil_cliente, cliente, "
            "libro_autor, libro, autor, genero, editorial, asignacion_rol, intento_acceso, "
            "evento_seguridad, usuario RESTART IDENTITY CASCADE"
        ))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()
