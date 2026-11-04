"""Envoltorio de listados y cálculo de páginas (Ejercicio 3).

Los listados devuelven {items, total, page, size, pages}:
- page empieza en 1
- size va de 1 a 100 (por defecto 20)
- pedir una página más allá de la última responde 422
- con cero resultados hay una página (pages = 1), vacía
"""

from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

from app.core.errores import DatosInvalidos
from app.core.parametros import MAX_ID

T = TypeVar("T")

PageQuery = Annotated[int, Query(ge=1, le=MAX_ID, description="Número de página (empieza en 1)")]
SizeQuery = Annotated[
    int, Query(ge=1, le=100, description="Tamaño de página (1 a 100, por defecto 20)")
]


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def calcular_paginas(total: int, page: int, size: int) -> tuple[int, int]:
    """Calcula la cantidad total de páginas y el offset para la consulta.

    Con cero resultados hay 1 página vacía. Si se pide una página mayor que
    la última, lanza DatosInvalidos (422) con el mensaje esperado.
    """
    pages = max(1, ceil(total / size)) if total > 0 else 1
    if page > pages:
        raise DatosInvalidos(f"La página {page} no existe: hay {pages}")
    offset = (page - 1) * size
    return pages, offset


def armar_pagina(items: list[T], total: int, page: int, size: int) -> Pagina[T]:
    pages, _ = calcular_paginas(total=total, page=page, size=size)
    return Pagina(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


def convertir_pagina(pagina: Pagina, esquema: type[BaseModel]) -> Pagina:
    """Pasa los items de una página de modelos de tabla a su contrato de salida.

    Se lee cada item por atributos (from_attributes), así que las relaciones que el
    repositorio precargó llegan a la respuesta. Si la conversión quedara en manos de
    la serialización por defecto, un modelo de tabla se volcaría sin sus relaciones.
    """
    return Pagina(
        items=[esquema.model_validate(item, from_attributes=True) for item in pagina.items],
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
        pages=pagina.pages,
    )
