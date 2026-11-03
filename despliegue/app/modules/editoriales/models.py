from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Editorial(SQLModel, table=True):
    """Agregación con Libro: la editorial existe por sí misma y la comparten muchos libros.

    La clave foránea va en libro (lado "muchos"): cada libro guarda el id de su editorial.
    """

    __tablename__ = "editorial"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120, unique=True)
    pais: str = Field(max_length=80)

    # lazy="raise": si alguna lectura olvidara precargar la relación, falla en lugar
    # de emitir consultas ocultas (prohibida la carga perezosa).
    libros: list["Libro"] = Relationship(
        back_populates="editorial", sa_relationship_kwargs={"lazy": "raise"}
    )
