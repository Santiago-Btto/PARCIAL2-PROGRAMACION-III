from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.parametros import IdPath, LimitQuery, OffsetQuery
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.ventas.schemas import VentaListado

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def crear_cliente(datos: ClienteCreate, session: SessionDep):
    return await service.crear(session, datos)


@router.get("/", response_model=list[ClienteRead])
async def listar_clientes(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0):
    return await service.listar(session, limit, offset)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def obtener_cliente(cliente_id: IdPath, session: SessionDep):
    return await service.obtener(session, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def actualizar_cliente(cliente_id: IdPath, datos: ClienteUpdate, session: SessionDep):
    return await service.actualizar(session, cliente_id, datos)


@router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED)
async def crear_perfil(cliente_id: IdPath, datos: PerfilCreate, session: SessionDep):
    return await service.crear_perfil(session, cliente_id, datos)


@router.get("/{cliente_id}/ventas", response_model=list[VentaListado])
async def listar_ventas_de_cliente(
    cliente_id: IdPath, session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0
):
    return await service.listar_ventas(session, cliente_id, limit, offset)
