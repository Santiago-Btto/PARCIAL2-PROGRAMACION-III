from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.ventas.models import RenglonVenta

ROLES_AUTORIA = ("autor", "coautor", "traductor", "ilustrador")


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="precio_positivo"),
        CheckConstraint("stock >= 0", name="stock_no_negativo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(max_length=20, unique=True)  # RN-01: lo garantiza la base
    titulo: str = Field(max_length=200)
    # Dinero siempre con Decimal -> NUMERIC(10,2), nunca float.
    precio: Decimal = Field(max_digits=10, decimal_places=2)
    stock: int = Field(default=0)

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
