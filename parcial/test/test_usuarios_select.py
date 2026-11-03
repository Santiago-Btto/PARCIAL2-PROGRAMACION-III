"""Regresiones del contrato escalar de SQLModel AsyncSession.exec."""

import pytest
from sqlmodel.sql.expression import SelectOfScalar

import app.core.modelos  # noqa: F401
from app.core.dependencies import get_roles_vigentes
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import UsuarioRepository


class _Resultado:
    def __init__(self, *, primero=None, filas=()):
        self._primero = primero
        self._filas = filas

    def first(self):
        return self._primero

    def all(self):
        return list(self._filas)


class _Session:
    def __init__(self, resultado):
        self.resultado = resultado
        self.statements = []

    async def exec(self, statement):
        self.statements.append(statement)
        return self.resultado


@pytest.mark.anyio
async def test_get_by_email_usa_select_escalar_y_devuelve_usuario():
    usuario = Usuario(
        id=7,
        email="admin@example.test",
        nombre="Admin",
        password_hash="hash-sintetico",
    )
    session = _Session(_Resultado(primero=usuario))

    encontrado = await UsuarioRepository(session).get_by_email(
        "  ADMIN@example.test "
    )

    assert encontrado is usuario
    assert len(session.statements) == 1
    assert isinstance(session.statements[0], SelectOfScalar)


@pytest.mark.anyio
async def test_roles_vigentes_usa_select_escalar_y_devuelve_nombres():
    usuario = Usuario(
        id=7,
        email="admin@example.test",
        nombre="Admin",
        password_hash="hash-sintetico",
    )
    session = _Session(_Resultado(filas=("ADMIN", "VENDEDOR")))

    roles = await get_roles_vigentes(usuario, session)

    assert roles == ["ADMIN", "VENDEDOR"]
    assert len(session.statements) == 1
    assert isinstance(session.statements[0], SelectOfScalar)


@pytest.mark.anyio
async def test_roles_vigentes_admite_usuario_sin_roles():
    usuario = Usuario(
        id=8,
        email="sin-roles@example.test",
        nombre="Sin roles",
        password_hash="hash-sintetico",
    )
    session = _Session(_Resultado())

    assert await get_roles_vigentes(usuario, session) == []
    assert isinstance(session.statements[0], SelectOfScalar)
