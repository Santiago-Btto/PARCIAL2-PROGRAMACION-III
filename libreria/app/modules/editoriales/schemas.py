from pydantic import field_validator
from sqlmodel import Field, SQLModel


class EditorialCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=120)
    pais: str = Field(min_length=1, max_length=80)


class EditorialUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    pais: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("nombre", "pais")
    @classmethod
    def no_nulo(cls, valor: str | None) -> str:
        # Omitir el campo es válido (PATCH parcial); enviarlo en null no lo es.
        if valor is None:
            raise ValueError("no puede ser nulo")
        return valor


class EditorialRead(SQLModel):
    id: int
    nombre: str
    pais: str
