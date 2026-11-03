from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, func, text
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import RenglonVenta, Venta

ROLES_AUTORIA = ("autor", "coautor", "traductor", "ilustrador")


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Libro(SQLModel, table=True):
    """Libro del catálogo con borrado lógico (`borrado_en`).

    RN-01 y RN-13: el ISBN deja de ser un UNIQUE común y pasa a ser único
    únicamente entre los libros vigentes (`WHERE borrado_en IS NULL`), de modo
    que un libro dado de baja conserva su fila para las ventas históricas pero
    su ISBN se puede volver a cargar.
    """

    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="precio_positivo"),
        CheckConstraint("stock >= 0", name="stock_no_negativo"),
        Index(
            "uq_libro_isbn_vigente",
            "isbn",
            unique=True,
            postgresql_where=text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(max_length=20)
    titulo: str = Field(max_length=200)
    # Dinero siempre con Decimal -> NUMERIC(10,2), nunca float.
    precio: Decimal = Field(max_digits=10, decimal_places=2)
    stock: int = Field(default=0)
    borrado_en: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    # Agregación: la FK va del lado "muchos" (libro). RESTRICT: no se puede borrar
    # una editorial que todavía tiene libros, porque la editorial no es "parte" del libro.
    editorial_id: int = Field(foreign_key="editorial.id", index=True, ondelete="RESTRICT")
    # Agregación opcional: nulo permitido. Si se borrara el género, el libro queda sin género.
    genero_id: int | None = Field(
        default=None, foreign_key="genero.id", index=True, ondelete="SET NULL"
    )

    editorial: Optional["Editorial"] = Relationship(
        back_populates="libros", sa_relationship_kwargs={"lazy": "raise"}
    )
    genero: Optional["Genero"] = Relationship(
        back_populates="libros", sa_relationship_kwargs={"lazy": "raise"}
    )
    autorias: list["LibroAutor"] = Relationship(
        back_populates="libro",
        sa_relationship_kwargs={
            "lazy": "raise",
            "cascade": "all, delete-orphan",
            "order_by": "LibroAutor.orden",
        },
    )
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="libro", sa_relationship_kwargs={"lazy": "raise"}
    )
    movimientos: list["MovimientoStock"] = Relationship(
        back_populates="libro",
        sa_relationship_kwargs={
            "lazy": "raise",
            "order_by": "MovimientoStock.id",
        },
    )


class LibroAutor(SQLModel, table=True):
    """Objeto de asociación del muchos a muchos Libro-Autor.

    Es una entidad con clase propia (no un link_model) porque tiene datos que no
    son ni del libro ni del autor: el rol y el orden en la tapa.
    Navegación: libro.autorias[i].autor y autor.autorias[i].libro.
    """

    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint("orden >= 1", name="orden_positivo"),
        CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')", name="rol_valido"
        ),
    )

    # Clave primaria compuesta (libro_id, autor_id): un autor figura una sola vez por libro.
    # Índices: el índice de la PK empieza por libro_id, así que ya sirve para buscar
    # por esa FK; autor_id no es la primera columna, por eso lleva su propio índice.
    libro_id: int = Field(foreign_key="libro.id", primary_key=True, ondelete="CASCADE")
    autor_id: int = Field(
        foreign_key="autor.id", primary_key=True, index=True, ondelete="RESTRICT"
    )
    rol: str = Field(max_length=20)
    orden: int

    libro: Optional["Libro"] = Relationship(
        back_populates="autorias", sa_relationship_kwargs={"lazy": "raise"}
    )
    autor: Optional["Autor"] = Relationship(
        back_populates="autorias", sa_relationship_kwargs={"lazy": "raise"}
    )


class MovimientoStock(SQLModel, table=True):
    """Registro de sólo agregado (append-only) de variaciones de stock (RN-11 y RN-12).

    El disparador instalado en la cuarta migración rechaza cualquier UPDATE o DELETE
    sobre esta tabla. Para cada libro se cumple siempre que `libro.stock` es igual
    a la suma de `cantidad` de sus movimientos.
    """

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        CheckConstraint("cantidad <> 0", name="cantidad_no_cero"),
    )

    id: int | None = Field(default=None, primary_key=True)
    libro_id: int = Field(foreign_key="libro.id", index=True, ondelete="RESTRICT")
    venta_id: int | None = Field(
        default=None,
        foreign_key="venta.id",
        index=True,
        ondelete="RESTRICT",
        nullable=True,
    )
    usuario_id: int = Field(
        foreign_key="usuario.id", index=True, ondelete="RESTRICT"
    )
    cantidad: int = Field(nullable=False)
    motivo: str = Field(max_length=200)
    cuando: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )

    libro: Optional["Libro"] = Relationship(
        back_populates="movimientos", sa_relationship_kwargs={"lazy": "raise"}
    )
    venta: Optional["Venta"] = Relationship(
        back_populates="movimientos_stock", sa_relationship_kwargs={"lazy": "raise"}
    )
    usuario: Optional["Usuario"] = Relationship(
        back_populates="movimientos_stock", sa_relationship_kwargs={"lazy": "raise"}
    )
