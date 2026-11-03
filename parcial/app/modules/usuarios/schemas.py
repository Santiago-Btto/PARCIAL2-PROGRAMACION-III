"""Contratos de entrada y salida del módulo usuarios (Ejercicios 3, 4 y 5).

- Todos los esquemas de entrada usan ConfigDict(extra="forbid").
- Ningún esquema de salida incluye password_hash.
- Validación de contraseñas de como máximo 72 bytes en UTF-8 (RN-15).
- Validación de vencimiento de rol con zona horaria obligatoria y en el futuro (RN-03).
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.usuarios.models import ROLES_SISTEMA

RolSistema = Literal["ADMIN", "VENDEDOR", "CLIENTE"]


def _validar_password_bytes(valor: str) -> str:
    if not valor or not valor.strip():
        raise ValueError("La contraseña no puede estar vacía.")
    if len(valor.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar los 72 bytes en UTF-8.")
    return valor


def _normalizar_email(valor: str) -> str:
    if isinstance(valor, str):
        return valor.strip().lower()
    return valor


# --- Esquemas de Entrada (extra="forbid") ---


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return _normalizar_email(v)

    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        return _validar_password_bytes(v)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return _normalizar_email(v)

    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        return _validar_password_bytes(v)


class CambiarPasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: str
    password_nueva: str

    @field_validator("password_actual", "password_nueva")
    @classmethod
    def validar_passwords(cls, v: str) -> str:
        return _validar_password_bytes(v)


class UsuarioCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    rol: RolSistema
    password_provisoria: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return _normalizar_email(v)

    @field_validator("password_provisoria")
    @classmethod
    def validar_password(cls, v: str) -> str:
        return _validar_password_bytes(v)


class AsignarRolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: RolSistema
    vence_en: datetime | None = None

    @field_validator("vence_en")
    @classmethod
    def validar_vencimiento(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("La fecha de vencimiento debe incluir zona horaria.")
        if v <= datetime.now(UTC):
            raise ValueError("La fecha de vencimiento debe estar en el futuro.")
        return v


# --- Esquemas de Salida (from_attributes=True, sin password_hash) ---


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool


class LoginOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mensaje: str = "Sesión iniciada"
    debe_cambiar_password: bool
    expira_en_segundos: int


class LogoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mensaje: str = "Sesión cerrada"


class YoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    roles_vigentes: list[str]
    roles_token: list[str]


class AsignacionRolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    otorgada_por: int | None = None


class EventoSeguridadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuando: datetime
    actor: str
    accion: str
