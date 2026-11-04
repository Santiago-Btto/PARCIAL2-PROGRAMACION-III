from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import UsuarioActualDep, requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery, convertir_pagina
from app.core.parametros import IdPath
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate, LibroDetalle, LibroListado, LibroUpdate, MovimientoStockRead, ReposicionCreate,
)
from app.modules.libros.unit_of_work import LibrosUowDep

router_publico = APIRouter(prefix="/libros", tags=["libros"])
router_protegido = APIRouter(
    prefix="/libros", tags=["libros"], dependencies=[Depends(requiere_rol("ADMIN"))]
)


@router_publico.get("/", response_model=Pagina[LibroListado])
async def listar_libros(
    uow: LibrosUowDep,
    page: PageQuery = 1,
    size: SizeQuery = 20,
    titulo: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    genero_id: int | None = None,
):
    pagina = await service.listar(uow, page=page, size=size, titulo=titulo, genero_id=genero_id)
    return convertir_pagina(pagina, LibroListado)


@router_publico.get("/{libro_id}", response_model=LibroDetalle)
async def obtener_libro(libro_id: IdPath, uow: LibrosUowDep):
    return LibroDetalle.desde(await service.obtener_detalle(uow, libro_id))


@router_protegido.post("/", response_model=LibroDetalle, status_code=status.HTTP_201_CREATED)
async def crear_libro(datos: LibroCreate, uow: LibrosUowDep, usuario: UsuarioActualDep):
    return LibroDetalle.desde(await service.crear(uow, datos, usuario_id=usuario.id))


@router_protegido.patch("/{libro_id}", response_model=LibroDetalle)
async def actualizar_libro(libro_id: IdPath, datos: LibroUpdate, uow: LibrosUowDep):
    return LibroDetalle.desde(await service.actualizar(uow, libro_id, datos))


@router_protegido.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_libro(libro_id: IdPath, uow: LibrosUowDep) -> Response:
    await service.eliminar(uow, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_protegido.post("/{libro_id}/reponer", response_model=LibroDetalle)
async def reponer_libro(
    libro_id: IdPath, datos: ReposicionCreate, uow: LibrosUowDep, usuario: UsuarioActualDep
):
    return LibroDetalle.desde(await service.reponer(uow, libro_id, datos, usuario_id=usuario.id))


@router_protegido.get("/{libro_id}/movimientos", response_model=Pagina[MovimientoStockRead])
async def listar_movimientos(
    libro_id: IdPath, uow: LibrosUowDep, page: PageQuery = 1, size: SizeQuery = 20
):
    return await service.listar_movimientos(uow, libro_id, page=page, size=size)
