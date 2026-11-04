from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery, convertir_pagina
from app.core.parametros import IdPath
from app.modules.editoriales import service
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate
from app.modules.editoriales.unit_of_work import EditorialesUowDep
from app.modules.libros.schemas import LibroListado


router_publico = APIRouter(prefix="/editoriales", tags=["editoriales"])
router_protegido = APIRouter(
    prefix="/editoriales", tags=["editoriales"], dependencies=[Depends(requiere_rol("ADMIN"))]
)


@router_protegido.post("/", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def crear_editorial(datos: EditorialCreate, uow: EditorialesUowDep):
    return await service.crear(uow, datos)


@router_publico.get("/", response_model=Pagina[EditorialRead])
async def listar_editoriales(
    uow: EditorialesUowDep, page: PageQuery = 1, size: SizeQuery = 20
):
    return await service.listar(uow, page=page, size=size)


@router_publico.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(editorial_id: IdPath, uow: EditorialesUowDep):
    return await service.obtener(uow, editorial_id)


@router_protegido.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(
    editorial_id: IdPath, datos: EditorialUpdate, uow: EditorialesUowDep
):
    return await service.actualizar(uow, editorial_id, datos)


@router_publico.get("/{editorial_id}/libros", response_model=Pagina[LibroListado])
async def listar_libros_de_editorial(
    editorial_id: IdPath, uow: EditorialesUowDep,
    page: PageQuery = 1, size: SizeQuery = 20,
):
    pagina = await service.listar_libros(uow, editorial_id, page=page, size=size)
    return convertir_pagina(pagina, LibroListado)
