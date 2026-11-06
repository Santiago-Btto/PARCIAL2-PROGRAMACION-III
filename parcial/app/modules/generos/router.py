from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery, convertir_pagina
from app.core.parametros import IdPath
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.generos.unit_of_work import GenerosUowDep
from app.modules.libros.schemas import LibroListado


router_publico = APIRouter(prefix="/generos", tags=["generos"])
router_protegido = APIRouter(
    prefix="/generos", tags=["generos"], dependencies=[Depends(requiere_rol("ADMIN"))]
)


@router_protegido.post(
    "", response_model=GeneroRead, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
@router_protegido.post("/", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def crear_genero(datos: GeneroCreate, uow: GenerosUowDep):
    return await service.crear(uow, datos)


@router_publico.get("", response_model=Pagina[GeneroRead], include_in_schema=False)
@router_publico.get("/", response_model=Pagina[GeneroRead])
async def listar_generos(
    uow: GenerosUowDep, page: PageQuery = 1, size: SizeQuery = 20
):
    return await service.listar(uow, page=page, size=size)


@router_publico.get("/{genero_id}/libros", response_model=Pagina[LibroListado])
async def listar_libros_de_genero(
    genero_id: IdPath, uow: GenerosUowDep,
    page: PageQuery = 1, size: SizeQuery = 20,
):
    pagina = await service.listar_libros(uow, genero_id, page=page, size=size)
    return convertir_pagina(pagina, LibroListado)
