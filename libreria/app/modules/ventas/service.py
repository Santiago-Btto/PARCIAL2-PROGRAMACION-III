import asyncio
import logging
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaCreate

logger = logging.getLogger("libreria.ventas")

CENTAVO = Decimal("0.01")

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
}


def consulta_listado() -> SelectOfScalar[Venta]:
    """Ventas con su cliente (relación a uno -> joinedload)."""
    return (
        select(Venta)
        .options(joinedload(Venta.cliente))  # type: ignore[arg-type]
        .order_by(col(Venta.id))
    )


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Venta]:
    consulta = consulta_listado().limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())


async def obtener(session: AsyncSession, venta_id: int) -> Venta:
    """Venta con cliente y renglones en un número FIJO de consultas (2):

    1. venta JOIN cliente                                  (joinedload, a uno)
    2. renglon_venta JOIN libro WHERE venta_id IN (...)    (selectinload de la colección
                                                            + joinedload del libro)
    No crece con la cantidad de renglones (caso C-07).
    """
    consulta = (
        select(Venta)
        .where(Venta.id == venta_id)
        .options(
            joinedload(Venta.cliente),  # type: ignore[arg-type]
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),  # type: ignore[arg-type]
        )
        .execution_options(populate_existing=True)
    )
    venta = (await session.exec(consulta)).first()
    if venta is None:
        raise NoEncontrado("La venta no existe.")
    return venta


async def crear(session: AsyncSession, datos: VentaCreate) -> Venta:
    """Alta de la venta junto con sus renglones (RN-04 a RN-07), en una sola transacción.

    - cliente_id: asociación. No se consulta antes: si no existe, la FK lo rechaza -> 409.
    - renglones: composición. Se agregan a venta.renglones y se insertan con la venta;
      no existe un alta de renglones por separado.
    - El precio de cada renglón se copia del libro leído de la base (RN-06) y el total
      lo calcula el servidor (RN-07).
    - El stock se descuenta; si no alcanza, el CHECK stock >= 0 de la base rechaza la escritura.
    """
    ids = [r.libro_id for r in datos.renglones]
    # Hay que leer los libros igual (para copiar su precio), así que un id inexistente
    # se detecta acá. FOR UPDATE bloquea esas filas hasta el commit: dos ventas
    # simultáneas del mismo libro no pisan el stock. El orden por id evita interbloqueos.
    consulta = select(Libro).where(col(Libro.id).in_(ids)).order_by(col(Libro.id)).with_for_update()
    libros = {libro.id: libro for libro in (await session.exec(consulta)).all()}
    faltantes = sorted(set(ids) - libros.keys())
    if faltantes:
        await session.rollback()
        raise Conflicto(f"No existe el libro con id {', '.join(map(str, faltantes))}.")

    venta = Venta(cliente_id=datos.cliente_id)
    total = Decimal("0.00")
    for renglon in datos.renglones:
        libro = libros[renglon.libro_id]
        venta.renglones.append(
            RenglonVenta(
                libro_id=renglon.libro_id,
                cantidad=renglon.cantidad,
                precio_unitario=libro.precio,  # RN-06: copia, no referencia
            )
        )
        total += libro.precio * renglon.cantidad
        libro.stock -= renglon.cantidad
    venta.total = total.quantize(CENTAVO)

    session.add(venta)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener(session, venta.id)  # type: ignore[arg-type]


async def avisar_comprobante(venta_id: int, email: str) -> None:
    """Tarea en segundo plano: corre DESPUÉS de enviar la respuesta.

    Recibe datos simples (no la sesión, que ya se cerró). Usa asyncio.sleep, que
    cede el control al bucle de eventos: mientras espera, el servidor sigue
    atendiendo otras peticiones. time.sleep bloquearía todo el proceso.
    """
    await asyncio.sleep(0.5)
    logger.info("Comprobante de la venta %s enviado a %s", venta_id, email)
