from typing import TYPE_CHECKING, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("usuario_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120)
    email: str = Field(max_length=254, unique=True)  # RN-01: lo garantiza la base
    # Acceso opcional por la web: nulo permitido y UNIQUE (uq_cliente_usuario_id).
    usuario_id: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        ondelete="SET NULL",
        nullable=True,
    )

    # Ejercicio 2: Cliente.usuario devuelve un objeto (o None) y no una lista.
    usuario: Optional["Usuario"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"lazy": "raise", "uselist": False},
    )
    # Uno a uno: uselist=False hace que Cliente.perfil devuelva un objeto (o None), no una lista.
    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"lazy": "raise", "uselist": False, "cascade": "all, delete-orphan"},
    )
    ventas: list["Venta"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise"}
    )


class PerfilCliente(SQLModel, table=True):
    """Uno a uno con Cliente.

    La FK va en perfil_cliente porque el perfil es el lado opcional (0..1) y
    depende del cliente: un cliente existe sin perfil, pero no al revés.
    El UNIQUE sobre cliente_id es lo que convierte el "muchos a uno" en "uno a uno".
    """

    __tablename__ = "perfil_cliente"

    id: int | None = Field(default=None, primary_key=True)
    # unique + index => un único índice UNIQUE, que además sirve como índice de la FK.
    cliente_id: int = Field(
        foreign_key="cliente.id", unique=True, index=True, ondelete="CASCADE"
    )
    telefono: str = Field(max_length=30)
    direccion: str = Field(max_length=200)

    cliente: Optional["Cliente"] = Relationship(
        back_populates="perfil", sa_relationship_kwargs={"lazy": "raise"}
    )
