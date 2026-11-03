from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.parametros import IdPath, LimitQuery, OffsetQuery
from app.modules.editoriales import service
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate
from app.modules.libros.schemas import LibroListado

router = APIRouter(prefix="/editoriales", tags=["editoriales"])


@router.post("/", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def crear_editorial(datos: EditorialCreate, session: SessionDep):
    return await service.crear(session, datos)


@router.get("/", response_model=list[EditorialRead])
async def listar_editoriales(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0):
    return await service.listar(session, limit, offset)


@router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(editorial_id: IdPath, session: SessionDep):
    return await service.obtener(session, editorial_id)


@router.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(editorial_id: IdPath, datos: EditorialUpdate, session: SessionDep):
    return await service.actualizar(session, editorial_id, datos)


@router.get("/{editorial_id}/libros", response_model=list[LibroListado])
async def listar_libros_de_editorial(
    editorial_id: IdPath, session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0
):
    return await service.listar_libros(session, editorial_id, limit, offset)
