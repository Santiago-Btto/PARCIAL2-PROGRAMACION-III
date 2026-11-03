import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

# Agregar parcial al sys.path
parcial_dir = Path(__file__).resolve().parent.parent
if str(parcial_dir) not in sys.path:
    sys.path.insert(0, str(parcial_dir))

from app.modules.usuarios.schemas import (
    AsignacionRolOut,
    AsignarRolIn,
    CambiarPasswordIn,
    EventoSeguridadOut,
    LoginIn,
    LoginOut,
    LogoutOut,
    RegistroIn,
    UsuarioCreateIn,
    UsuarioOut,
    YoOut,
)


def test_registro_in_valido():
    dto = RegistroIn(
        nombre="Juan Pérez",
        email="  JUAN@EXAMPLE.COM  ",
        password="claveSegura123",
    )
    assert dto.nombre == "Juan Pérez"
    assert dto.email == "juan@example.com"
    assert dto.password == "claveSegura123"


def test_registro_in_extra_forbid():
    with pytest.raises(ValidationError):
        RegistroIn(
            nombre="Juan",
            email="juan@example.com",
            password="clave",
            campo_extra="invalido",
        )


def test_password_max_72_bytes_utf8():
    # 73 bytes ASCII
    with pytest.raises(ValidationError) as exc_info:
        RegistroIn(
            nombre="Juan",
            email="juan@example.com",
            password="a" * 73,
        )
    assert "72 bytes" in str(exc_info.value)

    # Multi-byte UTF-8: 'ñ' tiene 2 bytes en UTF-8. 37 * 2 = 74 bytes (> 72)
    with pytest.raises(ValidationError) as exc_info:
        RegistroIn(
            nombre="Juan",
            email="juan@example.com",
            password="ñ" * 37,
        )
    assert "72 bytes" in str(exc_info.value)

    # 36 * 2 = 72 bytes -> Válido
    dto = RegistroIn(
        nombre="Juan",
        email="juan@example.com",
        password="ñ" * 36,
    )
    assert len(dto.password.encode("utf-8")) == 72


def test_login_in_validaciones():
    dto = LoginIn(email="  TEST@example.com ", password="password1")
    assert dto.email == "test@example.com"

    with pytest.raises(ValidationError):
        LoginIn(email="test@example.com", password="a" * 73)

    with pytest.raises(ValidationError):
        LoginIn(email="test@example.com", password="password", extra_field="bad")


def test_cambiar_password_in_validaciones():
    dto = CambiarPasswordIn(password_actual="antigua123", password_nueva="nueva123")
    assert dto.password_actual == "antigua123"
    assert dto.password_nueva == "nueva123"

    with pytest.raises(ValidationError):
        CambiarPasswordIn(password_actual="a" * 73, password_nueva="nueva123")

    with pytest.raises(ValidationError):
        CambiarPasswordIn(password_actual="antigua123", password_nueva="n" * 73)


def test_usuario_create_in_validaciones():
    dto = UsuarioCreateIn(
        nombre="Admin Uno",
        email="admin@libreria.com",
        rol="ADMIN",
        password_provisoria="prov123",
    )
    assert dto.rol == "ADMIN"

    with pytest.raises(ValidationError):
        UsuarioCreateIn(
            nombre="Admin Uno",
            email="admin@libreria.com",
            rol="ROL_INVALIDO",
            password_provisoria="prov123",
        )

    with pytest.raises(ValidationError):
        UsuarioCreateIn(
            nombre="Admin Uno",
            email="admin@libreria.com",
            rol="ADMIN",
            password_provisoria="p" * 73,
        )


def test_asignar_rol_in_validaciones():
    futuro = datetime.now(UTC) + timedelta(days=30)
    dto = AsignarRolIn(rol="VENDEDOR", vence_en=futuro)
    assert dto.rol == "VENDEDOR"
    assert dto.vence_en == futuro

    # Rol inválido
    with pytest.raises(ValidationError):
        AsignarRolIn(rol="SUPERADMIN")

    # vence_en naive (sin tzinfo)
    naive_dt = datetime.now() + timedelta(days=10)
    with pytest.raises(ValidationError) as exc_info:
        AsignarRolIn(rol="VENDEDOR", vence_en=naive_dt)
    assert "zona horaria" in str(exc_info.value)

    # vence_en en el pasado
    pasado = datetime.now(UTC) - timedelta(days=1)
    with pytest.raises(ValidationError) as exc_info:
        AsignarRolIn(rol="VENDEDOR", vence_en=pasado)
    assert "futuro" in str(exc_info.value)


def test_esquemas_salida_sin_password_hash():
    # LoginOut
    login_out = LoginOut(mensaje="Sesión iniciada", debe_cambiar_password=False, expira_en_segundos=1800)
    assert "password" not in login_out.model_dump()
    assert "token" not in login_out.model_dump()

    # UsuarioOut
    user_out = UsuarioOut(id=1, email="user@example.com", nombre="User", activo=True, debe_cambiar_password=False)
    assert "password_hash" not in user_out.model_dump()

    # YoOut
    yo_out = YoOut(
        id=1,
        email="user@example.com",
        nombre="User",
        activo=True,
        debe_cambiar_password=False,
        roles_vigentes=["ADMIN"],
        roles_token=["ADMIN"],
    )
    assert yo_out.roles_vigentes == ["ADMIN"]


def test_password_vacia_rechazada():
    with pytest.raises(ValidationError):
        RegistroIn(nombre="Juan", email="juan@example.com", password="")
    with pytest.raises(ValidationError):
        RegistroIn(nombre="Juan", email="juan@example.com", password="   ")


def test_vence_en_con_timezone_distinto_a_utc():
    from datetime import timezone
    tz_ar = timezone(timedelta(hours=-3))
    futuro_ar = datetime.now(tz_ar) + timedelta(days=2)
    dto = AsignarRolIn(rol="ADMIN", vence_en=futuro_ar)
    assert dto.vence_en == futuro_ar

