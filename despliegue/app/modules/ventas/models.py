from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import Libro


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Venta(SQLModel, table=True):
    """Registra un hecho: no tiene PATCH (RN-08)."""

    __tablename__ = "venta"
    __table_args__ = (CheckConstraint("total >= 0", name="total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    # Asociación con Cliente: la venta conoce al cliente (viaja su id), ninguno es parte
    # del otro. RESTRICT: no se borra un cliente con ventas registradas.
    cliente_id: int = Field(foreign_key="cliente.id", index=True, ondelete="RESTRICT")
    fecha: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    total: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)

    cliente: Optional["Cliente"] = Relationship(
        back_populates="ventas", sa_relationship_kwargs={"lazy": "raise"}
    )
    # Composición: los renglones nacen y mueren con la venta (cascade + delete-orphan
    # en el ORM y ON DELETE CASCADE en la base).
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="venta",
        sa_relationship_kwargs={
            "lazy": "raise",
            "cascade": "all, delete-orphan",
            "order_by": "RenglonVenta.id",
        },
    )


class RenglonVenta(SQLModel, table=True):
    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint("precio_unitario > 0", name="precio_unitario_positivo"),
        # RN-05 también en la base: un libro no se repite dentro de la misma venta.
        # Su índice empieza por venta_id, así que también cubre las búsquedas por esa FK.
        UniqueConstraint("venta_id", "libro_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Composición: la FK va en la parte (renglón), apuntando al todo (venta).
    venta_id: int = Field(foreign_key="venta.id", ondelete="CASCADE")
    # Asociación con Libro: el renglón nombra un libro que ya existe.
    libro_id: int = Field(foreign_key="libro.id", index=True, ondelete="RESTRICT")
    cantidad: int
    # RN-06: copia del precio del libro al momento de la venta; no cambia después.
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2)

    venta: Optional["Venta"] = Relationship(
        back_populates="renglones", sa_relationship_kwargs={"lazy": "raise"}
    )
    libro: Optional["Libro"] = Relationship(
        back_populates="renglones", sa_relationship_kwargs={"lazy": "raise"}
    )
