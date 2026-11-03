from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery
from app.core.parametros import IdPath
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate, LibroDeAutor
from app.modules.autores.unit_of_work import AutoresUowDep


router_publico = APIRouter(prefix="/autores", tags=["autores"])
router_protegido = APIRouter(
    prefix="/autores", tags=["autores"], dependencies=[Depends(requiere_rol("ADMIN"))]
)


@router_protegido.post("/", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def crear_autor(datos: AutorCreate, uow: AutoresUowDep):
    return await service.crear(uow, datos)


@router_publico.get("/", response_model=Pagina[AutorRead])
async def listar_autores(
    uow: AutoresUowDep, page: PageQuery = 1, size: SizeQuery = 20
):
    return await service.listar(uow, page=page, size=size)


@router_publico.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(autor_id: IdPath, uow: AutoresUowDep):
    return await service.obtener(uow, autor_id)


@router_protegido.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(
    autor_id: IdPath, datos: AutorUpdate, uow: AutoresUowDep
):
    return await service.actualizar(uow, autor_id, datos)


@router_publico.get("/{autor_id}/libros", response_model=Pagina[LibroDeAutor])
async def listar_libros_de_autor(
    autor_id: IdPath, uow: AutoresUowDep,
    page: PageQuery = 1, size: SizeQuery = 20,
):
    return await service.listar_libros(uow, autor_id, page=page, size=size)
