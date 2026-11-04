"""Reglas de ventas (RN-09, RN-10, RN-11 y RN-14) y aviso en segundo plano (Ejercicio 8).

El service recibe el Unit of Work sin abrir y lo abre con `async with`. Todo lo que
escribe el registro de una venta (la venta, sus renglones, el descuento de stock y
los movimientos) ocurre adentro de UN solo bloque: si algo falla en el medio, el
Unit of Work revierte y no queda ninguna de esas escrituras.
"""

import asyncio
import logging
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.errores import (
    Conflicto,
    MapaRestricciones,
    NoEncontrado,
    Prohibido,
    traducir_integrity_error,
)
from app.core.paginacion import Pagina, armar_pagina
from app.modules.libros.models import Libro
from app.modules.libros.stock import cambiar_stock
from app.modules.usuarios.models import Usuario
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaCreate
from app.modules.ventas.unit_of_work import VentasUnitOfWork

# Hijo de "uvicorn.error": con el arranque normal de uvicorn ese logger ya tiene
# su handler, así que el aviso se ve en la consola sin configurar nada más. Un
# logger propio sin configurar no aparecería con el registro por defecto.
logger = logging.getLogger("uvicorn.error.ventas")

CENTAVO = Decimal("0.01")
ROLES_PERSONAL = {"VENDEDOR", "ADMIN"}

ERRORES: MapaRestricciones = {
    "fk_venta_cliente_id_cliente": (Conflicto, "El cliente indicado no existe."),
    "fk_renglon_venta_libro_id_libro": (Conflicto, "Alguno de los libros indicados no existe."),
    "ck_libro_stock_no_negativo": (Conflicto, "No hay stock suficiente para alguno de los libros."),
    "uq_renglon_venta_venta_id_libro_id": (
        Conflicto,
        "Un mismo libro no puede aparecer en dos renglones.",
    ),
    "ck_renglon_venta_cantidad_positiva": (Conflicto, "La cantidad debe ser mayor que cero."),
    "ck_venta_total_no_negativo": (Conflicto, "El total de la venta no puede ser negativo."),
    "ck_movimiento_stock_cantidad_no_cero": (Conflicto, "La cantidad debe ser mayor que cero."),
}


async def crear(uow: VentasUnitOfWork, datos: VentaCreate, *, usuario_id: int) -> Venta:
    """Registra la venta y descuenta el stock en una sola transacción (RN-09 a RN-11).

    1. El cliente tiene que existir (409 si no).
    2. Cada libro se bloquea con SELECT ... FOR UPDATE en orden de id, para que dos
       ventas que comparten libros no se bloqueen en orden cruzado. Si un libro no
       existe, está dado de baja o no alcanza, responde 409 ANTES de escribir nada.
    3. El precio de cada renglón se copia del libro y el total lo calcula el servidor.
    4. Cada renglón descuenta su stock por `cambiar_stock`, el punto único de escritura
       de stock, que deja un movimiento negativo con la venta y el usuario que la registró.
    """
    venta_id: int
    try:
        async with uow:
            if await uow.clientes.get_by_id(datos.cliente_id) is None:
                raise Conflicto("El cliente indicado no existe.")

            libros: dict[int, Libro] = {}
            for renglon in sorted(datos.renglones, key=lambda r: r.libro_id):
                libro = await uow.libros.get_for_update(renglon.libro_id)
                if libro is None:
                    raise Conflicto(f"No existe el libro con id {renglon.libro_id}.")
                if libro.borrado_en is not None:
                    raise Conflicto(f"El libro «{libro.titulo}» está dado de baja.")
                if libro.stock < renglon.cantidad:
                    raise Conflicto(
                        f"No hay stock suficiente de «{libro.titulo}»: "
                        f"hay {libro.stock} y se piden {renglon.cantidad}."
                    )
                libros[renglon.libro_id] = libro

            venta = Venta(cliente_id=datos.cliente_id)
            total = Decimal("0.00")
            for renglon in datos.renglones:
                precio = libros[renglon.libro_id].precio  # RN-09: copia, no referencia
                venta.renglones.append(
                    RenglonVenta(
                        libro_id=renglon.libro_id,
                        cantidad=renglon.cantidad,
                        precio_unitario=precio,
                    )
                )
                total += precio * renglon.cantidad
            venta.total = total.quantize(CENTAVO)
            venta = await uow.ventas.add(venta)  # flush: la venta ya tiene id
            venta_id = venta.id  # type: ignore[assignment]

            for renglon in sorted(datos.renglones, key=lambda r: r.libro_id):
                await cambiar_stock(
                    uow,
                    libro_id=renglon.libro_id,
                    cantidad=-renglon.cantidad,
                    usuario_id=usuario_id,
                    motivo=f"Venta #{venta_id}",
                    venta_id=venta_id,
                )
    except IntegrityError as exc:
        await uow.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return await _detalle(uow, venta_id)


async def _detalle(uow: VentasUnitOfWork, venta_id: int) -> Venta:
    async with uow:
        venta = await uow.ventas.obtener_detalle(venta_id)
    if venta is None:
        raise NoEncontrado("La venta no existe.")
    return venta


async def listar(uow: VentasUnitOfWork, *, page: int, size: int) -> Pagina[Venta]:
    async with uow:
        return await uow.ventas.listar_pagina(page=page, size=size)


async def listar_propias(
    uow: VentasUnitOfWork, usuario: Usuario, *, page: int, size: int
) -> Pagina[Venta]:
    """Lo propio sólo pide estar autenticado (RN-14): las ventas de la ficha de
    cliente vinculada al usuario. Sin ficha, la página está vacía."""
    async with uow:
        cliente = await uow.clientes.obtener_por_usuario(usuario.id)  # type: ignore[arg-type]
        if cliente is None:
            return armar_pagina([], 0, page, size)
        return await uow.ventas.listar_pagina(page=page, size=size, cliente_id=cliente.id)


async def obtener(
    uow: VentasUnitOfWork, venta_id: int, *, usuario: Usuario, roles_vigentes: list[str]
) -> Venta:
    """Detalle de una venta para el personal o para el cliente dueño (RN-14).

    La ruta no lleva requiere_rol: un cliente no tiene rol de personal y recibiría
    403 al pedir su propia venta. Primero se resuelve quién es y qué relación tiene
    con la venta, y recién después qué se devuelve. El cliente se precarga con la
    venta, así que comprobar el dueño no agrega consultas.
    """
    venta = await _detalle(uow, venta_id)
    if ROLES_PERSONAL.intersection(roles_vigentes):
        return venta
    if venta.cliente is not None and venta.cliente.usuario_id == usuario.id:
        return venta
    raise Prohibido("No tenés permiso para ver esta venta.")


async def avisar_comprobante(venta_id: int, email: str) -> None:
    """Tarea en segundo plano: corre DESPUÉS de enviar la respuesta y sólo se agenda
    si la venta se confirmó.

    Recibe datos simples (no la sesión, que ya se cerró). Usa asyncio.sleep, que
    cede el control al bucle de eventos: mientras espera, el servidor sigue
    atendiendo otras peticiones. time.sleep bloquearía todo el proceso.
    """
    await asyncio.sleep(0.5)
    logger.info("Comprobante de la venta %s enviado a %s", venta_id, email)
