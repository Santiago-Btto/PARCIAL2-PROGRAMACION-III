from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, func, text
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock

ROLES_SISTEMA = ("ADMIN", "VENDEDOR", "CLIENTE")


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Usuario(SQLModel, table=True):
    """Cuenta de acceso al sistema.

    No tiene columna `rol`: los roles viven en `asignacion_rol` (página 6).
    """

    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=254, unique=True)
    nombre: str = Field(max_length=120)
    password_hash: str = Field(max_length=255)
    activo: bool = Field(default=True, nullable=False)
    debe_cambiar_password: bool = Field(default=False, nullable=False)

    # Uno a uno opcional con Cliente: la FK `usuario_id` vive en `cliente`.
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"lazy": "raise", "uselist": False},
    )
    asignaciones_rol: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "lazy": "raise",
            "foreign_keys": "[AsignacionRol.usuario_id]",
            "cascade": "all, delete-orphan",
        },
    )
    roles_otorgados: list["AsignacionRol"] = Relationship(
        back_populates="otorgador",
        sa_relationship_kwargs={
            "lazy": "raise",
            "foreign_keys": "[AsignacionRol.otorgada_por]",
        },
    )
    movimientos_stock: list["MovimientoStock"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"lazy": "raise"},
    )


class AsignacionRol(SQLModel, table=True):
    """Rol asignado a un usuario con vigencia e historial de revocación.

    RN-03: un usuario tiene a lo sumo una asignación abierta (`revocada_en IS NULL`)
    por cada rol, garantizado por el índice único parcial `uq_asignacion_rol_usuario_rol_abierta`.
    """

    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')",
            name="rol_valido",
        ),
        Index(
            "uq_asignacion_rol_usuario_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(
        foreign_key="usuario.id", index=True, ondelete="CASCADE"
    )
    rol: str = Field(max_length=20)
    desde: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    vence_en: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
    revocada_en: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
    otorgada_por: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        ondelete="SET NULL",
        nullable=True,
    )

    usuario: Optional["Usuario"] = Relationship(
        back_populates="asignaciones_rol",
        sa_relationship_kwargs={
            "lazy": "raise",
            "foreign_keys": "[AsignacionRol.usuario_id]",
        },
    )
    otorgador: Optional["Usuario"] = Relationship(
        back_populates="roles_otorgados",
        sa_relationship_kwargs={
            "lazy": "raise",
            "foreign_keys": "[AsignacionRol.otorgada_por]",
        },
    )


class IntentoAcceso(SQLModel, table=True):
    """Registro de intentos de inicio de sesión (RN-07 y Ejercicio 7).

    No se relaciona con ninguna otra tabla porque también registra intentos con
    correos que no pertenecen a ningún usuario, y se guarda en una sesión y
    transacción propias para sobrevivir al rollback de un login fallido.
    """

    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    email: str = Field(max_length=254)
    ip: str = Field(max_length=64)
    exito: bool = Field(nullable=False)


class EventoSeguridad(SQLModel, table=True):
    """Historial de eventos de seguridad (RN-16).

    `actor` es un texto (por ejemplo el correo del usuario o `SISTEMA` en el seed)
    y no se relaciona mediante clave foránea con ninguna otra tabla.
    """

    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    actor: str = Field(max_length=254)
    accion: str = Field(max_length=500)
