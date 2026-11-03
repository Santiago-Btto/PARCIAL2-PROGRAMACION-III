from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel


def _normalizar_email(valor: str) -> str:
    # Se guarda en minúsculas para que el UNIQUE de la base no deje pasar
    # "Ana@x.com" y "ana@x.com" como clientes distintos.
    return valor.strip().lower()


class ClienteCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return _normalizar_email(valor)


class ClienteUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = Field(default=None, max_length=254)

    @field_validator("nombre", "email")
    @classmethod
    def no_nulo(cls, valor: str | None) -> str:
        if valor is None:
            raise ValueError("no puede ser nulo")
        return valor

    @field_validator("email")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return _normalizar_email(valor)


class PerfilCreate(SQLModel):
    telefono: str = Field(min_length=6, max_length=30)
    direccion: str = Field(min_length=1, max_length=200)


class PerfilRead(SQLModel):
    id: int
    cliente_id: int
    telefono: str
    direccion: str


class ClienteResumen(SQLModel):
    id: int
    nombre: str
    email: str


class ClienteRead(ClienteResumen):
    """Cliente con su perfil: un objeto o null, nunca una lista."""

    perfil: PerfilRead | None
