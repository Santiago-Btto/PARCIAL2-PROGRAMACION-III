from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery, convertir_pagina
from app.core.parametros import IdPath
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.clientes.unit_of_work import ClientesUowDep
from app.modules.ventas.schemas import VentaListado

def _leer(cliente) -> ClienteRead:
    # Se lee por atributos para que el perfil precargado llegue a la respuesta.
    return ClienteRead.model_validate(cliente, from_attributes=True)


# Atención en el mostrador: sólo el personal (VENDEDOR o ADMIN). Se monta en el
# grupo protegido de main.py, que ya controla el cambio obligatorio de contraseña.
router_protegido = APIRouter(
    prefix="/clientes",
    tags=["clientes"],
    dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))],
)


@router_protegido.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def crear_cliente(datos: ClienteCreate, uow: ClientesUowDep):
    return _leer(await service.crear(uow, datos))


@router_protegido.get("/", response_model=Pagina[ClienteRead])
async def listar_clientes(uow: ClientesUowDep, page: PageQuery = 1, size: SizeQuery = 20):
    return convertir_pagina(await service.listar(uow, page=page, size=size), ClienteRead)


@router_protegido.get("/{cliente_id}", response_model=ClienteRead)
async def obtener_cliente(cliente_id: IdPath, uow: ClientesUowDep):
    return _leer(await service.obtener(uow, cliente_id))


@router_protegido.patch("/{cliente_id}", response_model=ClienteRead)
async def actualizar_cliente(cliente_id: IdPath, datos: ClienteUpdate, uow: ClientesUowDep):
    return _leer(await service.actualizar(uow, cliente_id, datos))


@router_protegido.post(
    "/{cliente_id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED
)
async def crear_perfil(cliente_id: IdPath, datos: PerfilCreate, uow: ClientesUowDep):
    return await service.crear_perfil(uow, cliente_id, datos)


@router_protegido.get("/{cliente_id}/ventas", response_model=Pagina[VentaListado])
async def listar_ventas_de_cliente(
    cliente_id: IdPath, uow: ClientesUowDep, page: PageQuery = 1, size: SizeQuery = 20
):
    pagina = await service.listar_ventas(uow, cliente_id, page=page, size=size)
    return convertir_pagina(pagina, VentaListado)
