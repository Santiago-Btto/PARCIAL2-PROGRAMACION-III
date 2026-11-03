import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import Request, Response
from fastapi.routing import APIRoute

parcial_dir = Path(__file__).resolve().parent.parent
if str(parcial_dir) not in sys.path:
    sys.path.insert(0, str(parcial_dir))

import app.core.modelos  # noqa: F401

from app.core.parametros import MAX_ID
from app.core.security import COOKIE_NAME
from app.modules.usuarios import router, service
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.router import (
    asignar_rol_endpoint,
    auth_router,
    cambiar_password_endpoint,
    crear_personal_endpoint,
    eventos_router,
    listar_eventos_endpoint,
    listar_roles,
    login,
    logout,
    registro,
    revocar_rol_endpoint,
    usuarios_router,
    yo,
)
from app.modules.usuarios.schemas import (
    AsignarRolIn,
    CambiarPasswordIn,
    LoginIn,
    LoginOut,
    RegistroIn,
    UsuarioCreateIn,
    UsuarioOut,
    YoOut,
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


def test_auth_router_handlers():
    uow = MagicMock()

    # 1. registro
    user_out = UsuarioOut(id=1, email="test@libreria.com", nombre="Test", activo=True, debe_cambiar_password=False)
    service.registrar_cliente = async_return(user_out)

    reg_in = RegistroIn(nombre="Test", email="test@libreria.com", password="password1")
    res_reg = run_async(registro(reg_in, uow))
    assert res_reg.email == "test@libreria.com"
    assert res_reg.id == 1

    # 2. login
    login_out = LoginOut(mensaje="Sesión iniciada", debe_cambiar_password=False, expira_en_segundos=1800)
    service.iniciar_sesion = async_return(("fake_token", 1800, login_out))

    request = MagicMock(spec=Request)
    request.client.host = "192.168.1.100"
    request.app.state.session_factory = MagicMock()
    request.app.state.dummy_password_hash = "dummy"

    response = Response()
    login_in = LoginIn(email="test@libreria.com", password="password1")
    res_login = run_async(login(request, response, login_in, uow))

    assert res_login.mensaje == "Sesión iniciada"
    assert "token" not in res_login.model_dump()
    # Verificar cookie en response
    set_cookie_header = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie_header
    assert "httponly" in set_cookie_header.lower()

    # 3. logout
    res_logout = run_async(logout(response))
    assert res_logout.mensaje == "Sesión cerrada"

    # 4. yo
    usuario_mock = Usuario(id=1, email="yo@libreria.com", nombre="Yo", password_hash="h", activo=True)
    yo_out = YoOut(
        id=1,
        email="yo@libreria.com",
        nombre="Yo",
        activo=True,
        debe_cambiar_password=False,
        roles_vigentes=["ADMIN"],
        roles_token=["ADMIN"],
    )
    service.obtener_perfil_yo = async_return(yo_out)
    res_yo = run_async(yo(uow, usuario_mock, {"roles": ["ADMIN"]}))
    assert res_yo.roles_vigentes == ["ADMIN"]

    # 5. cambiar-password
    service.cambiar_password = async_return({"mensaje": "Contraseña modificada correctamente."})
    pwd_in = CambiarPasswordIn(password_actual="antigua", password_nueva="nueva123")
    res_pwd = run_async(cambiar_password_endpoint(uow, usuario_mock, pwd_in))
    assert "correctamente" in res_pwd["mensaje"]


def test_usuarios_router_handlers():
    uow = MagicMock()
    admin_mock = Usuario(id=1, email="admin@libreria.com", nombre="Admin", password_hash="h", activo=True)

    # 1. crear_personal
    user_out = UsuarioOut(id=2, email="staff@libreria.com", nombre="Staff", activo=True, debe_cambiar_password=True)
    service.crear_personal = async_return(user_out)
    create_in = UsuarioCreateIn(nombre="Staff", email="staff@libreria.com", rol="VENDEDOR", password_provisoria="prov123")
    res_staff = run_async(crear_personal_endpoint(uow, admin_mock, create_in))
    assert res_staff.id == 2
    assert res_staff.debe_cambiar_password is True

    # 2. listar_roles
    asig = AsignacionRol(id=1, usuario_id=2, rol="VENDEDOR")
    service.listar_roles_usuario = async_return([asig])
    res_roles = run_async(listar_roles(2, uow, admin_mock))
    assert len(res_roles) == 1

    # 3. asignar_rol
    service.asignar_rol = async_return(asig)
    asig_in = AsignarRolIn(rol="VENDEDOR")
    res_asig = run_async(asignar_rol_endpoint(2, asig_in, uow, admin_mock))
    assert res_asig.rol == "VENDEDOR"

    # 4. revocar_rol
    asig_rev = AsignacionRol(id=1, usuario_id=2, rol="VENDEDOR", revocada_en=None)
    service.revocar_rol = async_return(asig_rev)
    res_rev = run_async(revocar_rol_endpoint(2, "VENDEDOR", uow, admin_mock))
    assert res_rev.rol == "VENDEDOR"


def test_rutas_declaradas_y_parametros_id_path():
    """Verifica que todas las rutas esperadas estén declaradas con sus métodos, códigos y parámetros."""
    # auth_router
    auth_rutas = {r.path: r for r in auth_router.routes if isinstance(r, APIRoute)}
    assert "/auth/registro" in auth_rutas
    assert auth_rutas["/auth/registro"].status_code == 201
    assert "POST" in auth_rutas["/auth/registro"].methods

    assert "/auth/login" in auth_rutas
    assert auth_rutas["/auth/login"].status_code == 200

    assert "/auth/logout" in auth_rutas
    assert auth_rutas["/auth/logout"].status_code == 200

    assert "/auth/yo" in auth_rutas
    assert "/auth/cambiar-password" in auth_rutas

    # usuarios_router
    usr_rutas = {r.path: r for r in usuarios_router.routes if isinstance(r, APIRoute)}
    assert "/usuarios" in usr_rutas
    assert "/usuarios/{id}/roles" in usr_rutas
    assert "/usuarios/{id}/roles/{rol}" in usr_rutas

    # Verificar que el parámetro de ruta `id` esté acotado con MAX_ID (IdPath)
    ruta_roles = usr_rutas["/usuarios/{id}/roles"]
    id_param = next(p for p in ruta_roles.dependant.path_params if p.name == "id")
    metadata_repr = str(id_param.field_info.metadata)
    assert str(MAX_ID) in metadata_repr
    assert "ge=1" in metadata_repr.lower() or "Ge(1)" in metadata_repr or "ge=1" in metadata_repr


def test_main_montaje_grupos_abierto_y_protegido():
    from main import grupo_abierto, grupo_protegido

    # auth_router debe estar en grupo_abierto
    rutas_abiertas = [r.path for r in grupo_abierto.routes]
    assert any("/auth" in p for p in rutas_abiertas)

    # usuarios_router y eventos_router deben estar en grupo_protegido
    rutas_protegidas = [r.path for r in grupo_protegido.routes]
    assert any("/usuarios" in p for p in rutas_protegidas)
    assert any("/eventos" in p for p in rutas_protegidas)
