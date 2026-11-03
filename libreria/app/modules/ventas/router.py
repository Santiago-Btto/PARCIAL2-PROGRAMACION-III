from fastapi import APIRouter, BackgroundTasks, status

from app.core.database import SessionDep
from app.core.parametros import IdPath, LimitQuery, OffsetQuery
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaListado, VentaRead

# RN-08: las ventas registran un hecho; no hay PATCH ni DELETE.
router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("/", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
async def crear_venta(datos: VentaCreate, tareas: BackgroundTasks, session: SessionDep):
    venta = await service.crear(session, datos)
    respuesta = VentaRead.desde(venta)
    # Se agenda con datos simples; corre después de enviar la respuesta.
    tareas.add_task(service.avisar_comprobante, respuesta.id, respuesta.cliente.email)
    return respuesta


@router.get("/", response_model=list[VentaListado])
async def listar_ventas(session: SessionDep, limit: LimitQuery = 20, offset: OffsetQuery = 0):
    return await service.listar(session, limit, offset)


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener_venta(venta_id: IdPath, session: SessionDep):
    return VentaRead.desde(await service.obtener(session, venta_id))
