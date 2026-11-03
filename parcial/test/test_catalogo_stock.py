"""Reglas del punto de stock; atomicidad y locking se prueban aparte en PostgreSQL."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.core.modelos  # noqa: F401
from app.core.errores import Conflicto, DatosInvalidos, NoEncontrado
from app.core.parametros import MAX_ID
from app.modules.libros.models import Libro
from app.modules.libros.stock import cambiar_stock


@pytest.fixture
def anyio_backend():
    return "asyncio"


class LibrosFake:
    def __init__(self, libro):
        self.libro = libro
        self.actualizados = []
        self.bloqueados = []

    async def get_for_update(self, libro_id):
        self.bloqueados.append(libro_id)
        return self.libro

    async def update(self, libro):
        self.actualizados.append(libro.stock)
        return libro


class MovimientosFake:
    def __init__(self):
        self.items = []

    async def add(self, movimiento):
        self.items.append(movimiento)
        return movimiento


def uow_fake(stock=5, *, inexistente=False, baja=False):
    libro = None if inexistente else Libro(
        id=1, isbn="978-950-000001-1", titulo="Prueba", precio="12.00", stock=stock,
        editorial_id=1, borrado_en=datetime.now(UTC) if baja else None,
    )
    return SimpleNamespace(libros=LibrosFake(libro), movimientos=MovimientosFake())


@pytest.mark.anyio
@pytest.mark.parametrize("cantidad,venta_id,esperado", [(3, None, 8), (-2, 8, 3), (-5, 9, 0)])
async def test_cambio_registra_variacion_actor_y_venta(cantidad, venta_id, esperado):
    uow = uow_fake()
    libro = await cambiar_stock(uow, libro_id=1, cantidad=cantidad, usuario_id=4,
                                motivo="Movimiento", venta_id=venta_id)
    assert libro.stock == esperado
    assert uow.libros.bloqueados == [1]
    assert uow.libros.actualizados == [esperado]
    movimiento, = uow.movimientos.items
    assert (movimiento.libro_id, movimiento.cantidad, movimiento.usuario_id,
            movimiento.venta_id, movimiento.motivo) == (1, cantidad, 4, venta_id, "Movimiento")


@pytest.mark.anyio
@pytest.mark.parametrize("stock,cantidad", [(1, -2), (MAX_ID, 1)])
async def test_cambio_rechaza_stock_fuera_de_rango_antes_de_escribir(stock, cantidad):
    uow = uow_fake(stock)
    with pytest.raises(Conflicto):
        await cambiar_stock(uow, libro_id=1, cantidad=cantidad, usuario_id=4, motivo="Prueba")
    assert uow.libros.libro.stock == stock
    assert uow.libros.actualizados == []
    assert uow.movimientos.items == []


@pytest.mark.anyio
@pytest.mark.parametrize("opciones,error", [({"inexistente": True}, NoEncontrado), ({"baja": True}, Conflicto)])
async def test_cambio_distingue_inexistente_y_baja(opciones, error):
    uow = uow_fake(**opciones)
    with pytest.raises(error):
        await cambiar_stock(uow, libro_id=1, cantidad=1, usuario_id=4, motivo="Prueba")
    assert uow.libros.actualizados == []
    assert uow.movimientos.items == []


@pytest.mark.anyio
@pytest.mark.parametrize("cantidad,motivo", [(0, "Prueba"), (1, "  "), (1, "x" * 201)])
async def test_cambio_rechaza_movimiento_invalido(cantidad, motivo):
    uow = uow_fake()
    with pytest.raises(DatosInvalidos):
        await cambiar_stock(uow, libro_id=1, cantidad=cantidad, usuario_id=4, motivo=motivo)
    assert uow.libros.actualizados == []
    assert uow.movimientos.items == []
