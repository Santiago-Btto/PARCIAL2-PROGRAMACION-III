from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.database import SessionDep
from app.core.parametros import MAX_ID, IdPath, LimitQuery, OffsetQuery
from app.modules.libros import service
from app.modules.libros.schemas import LibroCreate, LibroDetalle, LibroListado, LibroUpdate

router = APIRouter(prefix="/libros", tags=["libros"])


@router.post("/", response_model=LibroDetalle, status_code=status.HTTP_201_CREATED)
async def crear_libro(datos: LibroCreate, session: SessionDep):
    libro = await service.crear(session, datos)
    return LibroDetalle.desde(libro)


@router.get("/", response_model=list[LibroListado])
async def listar_libros(
    session: SessionDep,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
    titulo: Annotated[
        str | None, Query(min_length=1, max_length=200, description="Parte del título (sin distinguir mayúsculas)")
    ] = None,
    genero_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None,
):
    return await service.listar(session, limit, offset, titulo=titulo, genero_id=genero_id)


@router.get("/{libro_id}", response_model=LibroDetalle)
async def obtener_libro(libro_id: IdPath, session: SessionDep):
    return LibroDetalle.desde(await service.obtener_detalle(session, libro_id))


@router.patch("/{libro_id}", response_model=LibroDetalle)
async def actualizar_libro(libro_id: IdPath, datos: LibroUpdate, session: SessionDep):
    return LibroDetalle.desde(await service.actualizar(session, libro_id, datos))
