from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import RolesVigentesDep, UsuarioActualDep, requiere_rol
from app.core.paginacion import PageQuery, Pagina, SizeQuery, convertir_pagina
from app.core.parametros import IdPath
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaListado, VentaRead
from app.modules.ventas.unit_of_work import VentasUowDep

# Las ventas registran un hecho: no hay PATCH ni DELETE (RN-09).
# Todo se monta en el grupo protegido de main.py (sesión + cambio de clave resuelto).
router = APIRouter(prefix="/ventas", tags=["ventas"])
mis_ventas_router = APIRouter(tags=["ventas"])

solo_personal = [Depends(requiere_rol("VENDEDOR", "ADMIN"))]


@router.post(
    "",
    response_model=VentaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=solo_personal,
    include_in_schema=False,
)
@router.post(
    "/",
    response_model=VentaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=solo_personal,
)
async def crear_venta(
    datos: VentaCreate,
    tareas: BackgroundTasks,
    uow: VentasUowDep,
    usuario: UsuarioActualDep,
):
    venta = await service.crear(uow, datos, usuario_id=usuario.id)  # type: ignore[arg-type]
    respuesta = VentaRead.desde(venta)
    # Llegar acá significa que la transacción se confirmó: si la venta se hubiera
    # revertido, service.crear habría lanzado el error y la tarea no se agenda.
    # Se agenda con datos simples; corre después de enviar la respuesta.
    tareas.add_task(service.avisar_comprobante, respuesta.id, respuesta.cliente.email)
    return respuesta


@router.get("", response_model=Pagina[VentaListado], dependencies=solo_personal, include_in_schema=False)
@router.get("/", response_model=Pagina[VentaListado], dependencies=solo_personal)
async def listar_ventas(uow: VentasUowDep, page: PageQuery = 1, size: SizeQuery = 20):
    return convertir_pagina(await service.listar(uow, page=page, size=size), VentaListado)


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener_venta(
    venta_id: IdPath,
    uow: VentasUowDep,
    usuario: UsuarioActualDep,
    roles_vigentes: RolesVigentesDep,
):
    # Sin requiere_rol: el personal o el cliente dueño (lo decide el service).
    venta = await service.obtener(uow, venta_id, usuario=usuario, roles_vigentes=roles_vigentes)
    return VentaRead.desde(venta)


@mis_ventas_router.get("/mis-ventas", response_model=Pagina[VentaListado])
async def listar_mis_ventas(
    uow: VentasUowDep, usuario: UsuarioActualDep, page: PageQuery = 1, size: SizeQuery = 20
):
    pagina = await service.listar_propias(uow, usuario, page=page, size=size)
    return convertir_pagina(pagina, VentaListado)
