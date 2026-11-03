import re
from decimal import Decimal
from typing import Literal

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.core.parametros import MAX_ID
from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead
from app.modules.libros.models import Libro

RolAutoria = Literal["autor", "coautor", "traductor", "ilustrador"]

ISBN_PATRON = re.compile(r"^[0-9][0-9-]{8,15}[0-9Xx]$")


def _validar_isbn(valor: str) -> str:
    if not ISBN_PATRON.match(valor):
        raise ValueError("ISBN inválido: solo dígitos y guiones (el último puede ser X).")
    return valor


class AutoriaCreate(SQLModel):
    """Elemento de la lista "autores" del alta: el id del autor (ya existe)
    más los datos propios de la relación."""

    autor_id: int = Field(ge=1, le=MAX_ID)
    rol: RolAutoria
    orden: int = Field(ge=1, le=100)


class LibroCreate(SQLModel):
    isbn: str = Field(min_length=10, max_length=20)
    titulo: str = Field(min_length=1, max_length=200)
    precio: Decimal = Field(gt=0, max_digits=10, decimal_places=2)  # RN-03
    stock: int = Field(default=0, ge=0, le=MAX_ID)  # RN-03
    editorial_id: int = Field(ge=1, le=MAX_ID)
    genero_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    autores: list[AutoriaCreate] = Field(min_length=1)

    @field_validator("isbn")
    @classmethod
    def isbn_valido(cls, valor: str) -> str:
        return _validar_isbn(valor)

    @model_validator(mode="after")
    def autorias_sin_repetir(self) -> "LibroCreate":
        if not self.autores:
            raise ValueError("El libro necesita al menos un autor.")
        ids = [a.autor_id for a in self.autores]
        if len(ids) != len(set(ids)):
            raise ValueError("Un mismo autor no puede figurar dos veces en el libro.")
        ordenes = [a.orden for a in self.autores]
        if len(ordenes) != len(set(ordenes)):
            raise ValueError("Dos autorías no pueden tener el mismo orden.")
        return self


class LibroUpdate(SQLModel):
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    precio: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0, le=MAX_ID)
    editorial_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    # genero_id sí acepta null explícito: quita el género (agregación opcional).
    genero_id: int | None = Field(default=None, ge=1, le=MAX_ID)

    @field_validator("isbn", "titulo", "precio", "stock", "editorial_id")
    @classmethod
    def no_nulo(cls, valor: object) -> object:
        if valor is None:
            raise ValueError("no puede ser nulo")
        return valor

    @field_validator("isbn")
    @classmethod
    def isbn_valido(cls, valor: str | None) -> str | None:
        return _validar_isbn(valor) if valor is not None else valor


class AutoriaRead(SQLModel):
    autor_id: int
    nombre: str
    rol: str
    orden: int


class LibroListado(SQLModel):
    """Libro con editorial y género (listados)."""

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialRead
    genero: GeneroRead | None


class LibroDetalle(LibroListado):
    """Libro con editorial, género y autores (detalle)."""

    autores: list[AutoriaRead]

    @classmethod
    def desde(cls, libro: Libro) -> "LibroDetalle":
        # Solo lee relaciones que la consulta precargó (lazy="raise" lo garantiza).
        return cls(
            id=libro.id,  # type: ignore[arg-type]
            isbn=libro.isbn,
            titulo=libro.titulo,
            precio=libro.precio,
            stock=libro.stock,
            editorial=EditorialRead.model_validate(libro.editorial),
            genero=GeneroRead.model_validate(libro.genero) if libro.genero else None,
            autores=[
                AutoriaRead(
                    autor_id=a.autor_id,
                    nombre=a.autor.nombre if a.autor else "",
                    rol=a.rol,
                    orden=a.orden,
                )
                for a in libro.autorias
            ],
        )
