from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.parametros import IdPath, LimitQuery, OffsetQuery
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.libros.schemas import LibroListado

router = APIRouter(prefix="/generos", tags=["generos"])


@router.post("/", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def crear_genero(datos: GeneroCreate, session: SessionDep):
    return await service.crear(session, datos)


@router.get("/", response_model=list[GeneroRead])
async def listar_generos(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0):
    return await service.listar(session, limit, offset)


@router.get("/{genero_id}/libros", response_model=list[LibroListado])
async def listar_libros_de_genero(
    genero_id: IdPath, session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0
):
    return await service.listar_libros(session, genero_id, limit, offset)
