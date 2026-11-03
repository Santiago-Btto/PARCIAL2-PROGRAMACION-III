from decimal import Decimal

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class AutorCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=120)
    nacionalidad: str = Field(min_length=1, max_length=60)


class AutorUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    nacionalidad: str | None = Field(default=None, min_length=1, max_length=60)

    @field_validator("nombre", "nacionalidad")
    @classmethod
    def no_nulo(cls, valor: str | None) -> str:
        if valor is None:
            raise ValueError("no puede ser nulo")
        return valor


class AutorRead(SQLModel):
    id: int
    nombre: str
    nacionalidad: str


class LibroDeAutor(SQLModel):
    """Un libro visto desde el autor, con los datos de la relación (rol y orden)."""

    libro_id: int
    isbn: str
    titulo: str
    precio: Decimal
    rol: str
    orden: int
