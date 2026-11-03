from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  aplica la convención de nombres antes de declarar la tabla

if TYPE_CHECKING:
    from app.modules.libros.models import LibroAutor


class Autor(SQLModel, table=True):
    __tablename__ = "autor"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120)
    nacionalidad: str = Field(max_length=60)

    # Muchos a muchos con datos: el autor no ve "libros" directamente sino sus
    # autorías (objeto de asociación LibroAutor), que llevan el rol y el orden.
    autorias: list["LibroAutor"] = Relationship(
        back_populates="autor", sa_relationship_kwargs={"lazy": "raise"}
    )
