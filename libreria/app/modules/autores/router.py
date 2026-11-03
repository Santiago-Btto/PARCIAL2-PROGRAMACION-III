from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.parametros import IdPath, LimitQuery, OffsetQuery
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate, LibroDeAutor

router = APIRouter(prefix="/autores", tags=["autores"])


@router.post("/", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def crear_autor(datos: AutorCreate, session: SessionDep):
    return await service.crear(session, datos)


@router.get("/", response_model=list[AutorRead])
async def listar_autores(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0):
    return await service.listar(session, limit, offset)


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(autor_id: IdPath, session: SessionDep):
    return await service.obtener(session, autor_id)


@router.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(autor_id: IdPath, datos: AutorUpdate, session: SessionDep):
    return await service.actualizar(session, autor_id, datos)


@router.get("/{autor_id}/libros", response_model=list[LibroDeAutor])
async def listar_libros_de_autor(
    autor_id: IdPath, session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0
):
    return await service.listar_libros(session, autor_id, limit, offset)
