import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

parcial_dir = Path(__file__).resolve().parent.parent
if str(parcial_dir) not in sys.path:
    sys.path.insert(0, str(parcial_dir))

import app.core.modelos  # noqa: F401

from app.core.errores import Conflicto, DemasiadosIntentos, NoAutenticado, NoEncontrado
from app.core.security import hashear_password
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.schemas import (
    AsignarRolIn,
    CambiarPasswordIn,
    LoginIn,
    RegistroIn,
    UsuarioCreateIn,
)
from app.modules.usuarios.service import (
    asignar_rol,
    cambiar_password,
    crear_personal,
    iniciar_sesion,
    listar_eventos,
    listar_roles_usuario,
    obtener_perfil_yo,
    registrar_cliente,
    revocar_rol,
)


def run_async(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def async_return(val):
    async def _coro(*args, **kwargs):
        return val
    return _coro


def async_spy(val=None):
    spy = MagicMock()
    async def _coro(*args, **kwargs):
        spy(*args, **kwargs)
        return val
    _coro.spy = spy
    return _coro


def test_registrar_cliente_exito():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    async def _add_usuario(u):
        u.id = 1
        return u

    async def _add_rol(r):
        r.id = 1
        return r

    async def _add_cliente(c):
        c.id = 1
        return c

    uow.usuarios.add = _add_usuario
    uow.asignaciones_rol.add = _add_rol
    uow.clientes.add = _add_cliente

    datos = RegistroIn(nombre="Carlos", email="carlos@example.com", password="claveSegura123")
    res = run_async(registrar_cliente(uow, datos))
    assert res.id == 1
    assert res.email == "carlos@example.com"
    assert res.nombre == "Carlos"


def test_iniciar_sesion_limite_intentos_rn07():
    uow = MagicMock()
    uow.intentos_acceso.contar_fallos_recientes = async_return(5)
    uow.intentos_acceso.calcular_retry_after = async_return(45)

    datos = LoginIn(email="bloqueado@example.com", password="password1")
    session_factory = MagicMock()

    with pytest.raises(DemasiadosIntentos) as exc_info:
        run_async(iniciar_sesion(uow, session_factory, datos, ip="127.0.0.1", dummy_password_hash="dummy"))

    assert exc_info.value.retry_after == 45
    assert "45" in exc_info.value.headers["Retry-After"]


def test_iniciar_sesion_usuario_inexistente_rn08():
    uow = MagicMock()
    uow.intentos_acceso.contar_fallos_recientes = async_return(0)
    uow.usuarios.get_by_email = async_return(None)

    sesion_propia = MagicMock()
    sesion_propia.commit = async_return(None)

    class MockCtx:
        async def __aenter__(self):
            return sesion_propia

        async def __aexit__(self, *args):
            pass

    session_factory = MagicMock(return_value=MockCtx())

    datos = LoginIn(email="inexistente@example.com", password="password1")
    # Generar un hash ficticio real para verificar
    dummy_hash = run_async(hashear_password("dummy"))

    with pytest.raises(NoAutenticado) as exc_info:
        run_async(iniciar_sesion(uow, session_factory, datos, ip="127.0.0.1", dummy_password_hash=dummy_hash))

    assert "Credenciales inválidas" in str(exc_info.value)
    sesion_propia.add.assert_called_once()


def test_iniciar_sesion_exitoso():
    uow = MagicMock()
    uow.intentos_acceso.contar_fallos_recientes = async_return(0)
    pwd_hash = run_async(hashear_password("correcta123"))
    user = Usuario(id=1, email="ana@example.com", nombre="Ana", password_hash=pwd_hash, activo=True, debe_cambiar_password=False)
    uow.usuarios.get_by_email = async_return(user)
    uow.asignaciones_rol.get_roles_vigentes_nombres = async_return(["CLIENTE"])

    sesion_propia = MagicMock()
    sesion_propia.commit = async_return(None)

    class MockCtx:
        async def __aenter__(self):
            return sesion_propia

        async def __aexit__(self, *args):
            pass

    session_factory = MagicMock(return_value=MockCtx())
    datos = LoginIn(email="ana@example.com", password="correcta123")

    token, expira, login_out = run_async(iniciar_sesion(uow, session_factory, datos, ip="127.0.0.1", dummy_password_hash="dummy"))
    assert token is not None
    assert expira > 0
    assert login_out.mensaje == "Sesión iniciada"
    assert login_out.debe_cambiar_password is False


def test_cambiar_password():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)
    uow.usuarios.update = async_return(None)
    evento_add_spy = async_spy(None)
    uow.eventos_seguridad.add = evento_add_spy

    pwd_hash = run_async(hashear_password("claveVieja123"))
    user = Usuario(id=1, email="user@example.com", nombre="User", password_hash=pwd_hash, activo=True, debe_cambiar_password=True)

    # Clave actual errónea
    with pytest.raises(NoAutenticado):
        datos_erroneos = CambiarPasswordIn(password_actual="incorrecta", password_nueva="claveNueva123")
        run_async(cambiar_password(uow, user, datos_erroneos))

    # Clave actual correcta
    datos_correctos = CambiarPasswordIn(password_actual="claveVieja123", password_nueva="claveNueva123")
    res = run_async(cambiar_password(uow, user, datos_correctos))
    assert "correctamente" in res["mensaje"]
    evento_add_spy.spy.assert_called_once()


def test_crear_personal():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    async def _add_user(u):
        u.id = 2
        return u

    uow.usuarios.add = _add_user
    uow.asignaciones_rol.add = async_return(None)
    evento_add_spy = async_spy(None)
    uow.eventos_seguridad.add = evento_add_spy

    admin = Usuario(id=1, email="admin@libreria.com", nombre="Admin", password_hash="h", activo=True)
    datos = UsuarioCreateIn(nombre="Vendedor Uno", email="vend@libreria.com", rol="VENDEDOR", password_provisoria="prov123")

    res = run_async(crear_personal(uow, admin, datos))
    assert res.id == 2
    assert res.email == "vend@libreria.com"
    assert res.debe_cambiar_password is True
    evento_add_spy.spy.assert_called_once()


def test_asignar_rol_cierra_vencido_y_abre_nuevo():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    admin = Usuario(id=1, email="admin@libreria.com", nombre="Admin", password_hash="h", activo=True)
    user = Usuario(id=2, email="user@libreria.com", nombre="User", password_hash="h", activo=True)
    uow.usuarios.get_by_id = async_return(user)

    # Asignación abierta pero vencida en el pasado
    pasado = datetime.now(UTC) - timedelta(days=5)
    asig_vencida = AsignacionRol(id=10, usuario_id=2, rol="VENDEDOR", vence_en=pasado, revocada_en=None)
    uow.asignaciones_rol.get_abierta_por_usuario_y_rol = async_return(asig_vencida)

    async def _update_asig(entidad, cambios):
        for k, v in cambios.items():
            setattr(entidad, k, v)
        return entidad

    uow.asignaciones_rol.update = _update_asig
    uow.asignaciones_rol.add = async_return(None)
    evento_add_spy = async_spy(None)
    uow.eventos_seguridad.add = evento_add_spy

    futuro = datetime.now(UTC) + timedelta(days=30)
    datos = AsignarRolIn(rol="VENDEDOR", vence_en=futuro)

    nueva = run_async(asignar_rol(uow, admin, usuario_id=2, datos=datos))
    assert nueva.rol == "VENDEDOR"
    assert asig_vencida.revocada_en is not None
    evento_add_spy.spy.assert_called_once()


def test_asignar_rol_conflicto_si_esta_vigente():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    admin = Usuario(id=1, email="admin@libreria.com", nombre="Admin", password_hash="h", activo=True)
    user = Usuario(id=2, email="user@libreria.com", nombre="User", password_hash="h", activo=True)
    uow.usuarios.get_by_id = async_return(user)

    # Asignación abierta vigente (vence_en es None)
    asig_vigente = AsignacionRol(id=10, usuario_id=2, rol="VENDEDOR", vence_en=None, revocada_en=None)
    uow.asignaciones_rol.get_abierta_por_usuario_y_rol = async_return(asig_vigente)

    futuro = datetime.now(UTC) + timedelta(days=30)
    datos = AsignarRolIn(rol="VENDEDOR", vence_en=futuro)

    with pytest.raises(Conflicto) as exc_info:
        run_async(asignar_rol(uow, admin, usuario_id=2, datos=datos))
    assert "vigente" in str(exc_info.value)


def test_revocar_rol_autoproteccion_admin_rn05():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    admin = Usuario(id=1, email="admin@libreria.com", nombre="Admin", password_hash="h", activo=True)
    uow.usuarios.get_by_id = async_return(admin)
    asig_abierta = AsignacionRol(id=1, usuario_id=1, rol="ADMIN")
    uow.asignaciones_rol.get_abierta_por_usuario_y_rol = async_return(asig_abierta)

    # Intento de auto-revocación
    with pytest.raises(Conflicto) as exc_info:
        run_async(revocar_rol(uow, admin_actual=admin, usuario_id=1, rol="ADMIN"))
    assert "propio rol ADMIN" in str(exc_info.value)


def test_revocar_rol_ultimo_admin_rn05():
    uow = MagicMock()
    uow.__aenter__ = async_return(uow)
    uow.__aexit__ = async_return(None)

    admin_1 = Usuario(id=1, email="admin1@libreria.com", nombre="Admin 1", password_hash="h", activo=True)
    admin_2 = Usuario(id=2, email="admin2@libreria.com", nombre="Admin 2", password_hash="h", activo=True)

    uow.usuarios.get_by_id = async_return(admin_2)
    asig_abierta = AsignacionRol(id=10, usuario_id=2, rol="ADMIN")
    uow.asignaciones_rol.get_abierta_por_usuario_y_rol = async_return(asig_abierta)
    # 0 otros admins vigentes
    uow.asignaciones_rol.contar_admins_vigentes = async_return(0)

    with pytest.raises(Conflicto) as exc_info:
        run_async(revocar_rol(uow, admin_actual=admin_1, usuario_id=2, rol="ADMIN"))
    assert "sin administradores vigentes" in str(exc_info.value)


def test_listar_eventos_paginado():
    uow = MagicMock()
    uow.eventos_seguridad.count = async_return(1)
    ev = EventoSeguridad(id=1, cuando=datetime.now(UTC), actor="admin@libreria.com", accion="Prueba")
    uow.eventos_seguridad.listar_paginado = async_return([ev])

    pagina = run_async(listar_eventos(uow, page=1, size=20))
    assert pagina.total == 1
    assert pagina.page == 1
    assert len(pagina.items) == 1
    assert pagina.items[0].actor == "admin@libreria.com"
