import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

parcial_dir = Path(__file__).resolve().parent.parent
if str(parcial_dir) not in sys.path:
    sys.path.insert(0, str(parcial_dir))

import app.core.modelos  # noqa: F401  registra todas las tablas y relaciones

from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
    registrar_intento_acceso_independiente,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork, get_usuarios_uow


def run_async(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def async_return(val):
    async def _coro(*args, **kwargs):
        return val
    return _coro


def test_usuario_repository_get_by_email():
    session = MagicMock()
    repo = UsuarioRepository(session)
    mock_result = MagicMock()
    mock_user = Usuario(id=1, email="test@example.com", nombre="Test", password_hash="hash")
    mock_result.first.return_value = mock_user
    session.exec = async_return(mock_result)

    user = run_async(repo.get_by_email("  TEST@example.com "))
    assert user == mock_user


def test_asignacion_rol_repository_metodos():
    session = MagicMock()
    repo = AsignacionRolRepository(session)

    # get_by_usuario
    mock_result = MagicMock()
    mock_result.all.return_value = [
        AsignacionRol(id=1, usuario_id=2, rol="CLIENTE"),
    ]
    session.exec = async_return(mock_result)
    roles = run_async(repo.get_by_usuario(2))
    assert len(roles) == 1
    assert roles[0].rol == "CLIENTE"

    # get_roles_vigentes_nombres
    mock_result_nombres = MagicMock()
    mock_result_nombres.all.return_value = ["ADMIN", "VENDEDOR"]
    session.exec = async_return(mock_result_nombres)
    nombres = run_async(repo.get_roles_vigentes_nombres(2))
    assert nombres == ["ADMIN", "VENDEDOR"]

    # get_abierta_por_usuario_y_rol
    mock_result_abierta = MagicMock()
    asig_abierta = AsignacionRol(id=5, usuario_id=2, rol="ADMIN")
    mock_result_abierta.first.return_value = asig_abierta
    session.exec = async_return(mock_result_abierta)
    res = run_async(repo.get_abierta_por_usuario_y_rol(2, "ADMIN"))
    assert res == asig_abierta

    # contar_admins_vigentes
    session.scalar = async_return(2)
    count = run_async(repo.contar_admins_vigentes(excluir_usuario_id=1))
    assert count == 2


def test_intento_acceso_repository_contar_fallos_recientes():
    session = MagicMock()
    repo = IntentoAccesoRepository(session)

    respuestas = [None, 3]

    async def _mock_scalar(*args, **kwargs):
        return respuestas.pop(0)

    session.scalar = _mock_scalar
    fallos = run_async(
        repo.contar_fallos_recientes(
            "user@example.com", "127.0.0.1", datetime.now(UTC) - timedelta(seconds=60)
        )
    )
    assert fallos == 3


def test_registrar_intento_acceso_independiente_sesion_propia():
    commit_spy = MagicMock()

    async def _commit():
        commit_spy()

    sesion_propia = MagicMock()
    sesion_propia.commit = _commit

    class MockContextManager:
        async def __aenter__(self):
            return sesion_propia

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    fabrica = MagicMock(return_value=MockContextManager())

    intento = run_async(
        registrar_intento_acceso_independiente(
            fabrica,
            email="test@example.com",
            ip="127.0.0.1",
            exito=False,
        )
    )
    assert intento.email == "test@example.com"
    assert intento.exito is False
    sesion_propia.add.assert_called_once()
    commit_spy.assert_called_once()


def test_usuarios_unit_of_work_repositorios_y_transaccion():
    commit_spy = MagicMock()
    rollback_spy = MagicMock()

    async def _commit():
        commit_spy()

    async def _rollback():
        rollback_spy()

    session = MagicMock()
    session.commit = _commit
    session.rollback = _rollback
    uow = UsuariosUnitOfWork(session)

    assert isinstance(uow.usuarios, UsuarioRepository)
    assert isinstance(uow.asignaciones_rol, AsignacionRolRepository)
    assert isinstance(uow.intentos_acceso, IntentoAccesoRepository)
    assert isinstance(uow.eventos_seguridad, EventoSeguridadRepository)
    assert uow.clientes.model_cls == Cliente

    async def _bloque():
        async with uow:
            pass

    run_async(_bloque())
    commit_spy.assert_called_once()
    rollback_spy.assert_not_called()


def test_usuarios_unit_of_work_rollback_on_error():
    commit_spy = MagicMock()
    rollback_spy = MagicMock()

    async def _commit():
        commit_spy()

    async def _rollback():
        rollback_spy()

    session = MagicMock()
    session.commit = _commit
    session.rollback = _rollback
    uow = UsuariosUnitOfWork(session)

    async def _bloque():
        async with uow:
            raise ValueError("Error simulado")

    with pytest.raises(ValueError):
        run_async(_bloque())

    commit_spy.assert_not_called()
    rollback_spy.assert_called_once()



def test_get_usuarios_uow_dependencia():
    session = MagicMock()
    uow = get_usuarios_uow(session)
    assert isinstance(uow, UsuariosUnitOfWork)
    assert uow.session == session
