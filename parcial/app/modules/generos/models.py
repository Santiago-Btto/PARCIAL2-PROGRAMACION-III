from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Genero(SQLModel, table=True):
    """Agregación opcional con Libro: la FK libro.genero_id admite nulo."""

    __tablename__ = "genero"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=60, unique=True)

    libros: list["Libro"] = Relationship(
        back_populates="genero", sa_relationship_kwargs={"lazy": "raise"}
    )
