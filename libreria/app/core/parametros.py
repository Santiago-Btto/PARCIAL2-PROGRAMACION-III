"""Parámetros tipados compartidos por los routers."""

from typing import Annotated

from fastapi import Path, Query

# Los id de PostgreSQL son INTEGER (32 bits). Acotar el rango evita que un valor
# enorme llegue a la base y produzca un error del controlador en lugar de un 422.
MAX_ID = 2_147_483_647

IdPath = Annotated[int, Path(ge=1, le=MAX_ID, description="Identificador del recurso")]

# RN-10: todo listado se pagina con limit (1 a 100, por defecto 20) y offset (desde 0).
LimitQuery = Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de resultados")]
OffsetQuery = Annotated[int, Query(ge=0, le=MAX_ID, description="Resultados a saltear")]
