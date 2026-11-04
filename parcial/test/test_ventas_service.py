"""Reglas del registro y la lectura de ventas con dobles del Unit of Work.

La atomicidad real (que el rollback no deje filas) y el disparador se prueban
contra PostgreSQL con los casos .http; acá se verifica qué decide el service.
"""

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.core.modelos  # noqa: F401
from app.core.errores import Conflicto, NoEncontrado, Prohibido
from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro
from app.modules.usuarios.models import Usuario
from app.modules.ventas import service
from app.modules.ventas.schemas import RenglonCreate, VentaCreate


@pytest.fixture
def anyio_backend():
    return "asyncio"


def libro(libro_id, titulo, precio, stock, *, baja=False):
    return Libro(
        id=libro_id, isbn=f"978-950-00-000{libro_id}-0", titulo=titulo, precio=Decimal(precio),
        stock=stock, editorial_id=1, borrado_en=datetime.now(UTC) if baja else None,
    )


class LibrosFake:
    def __init__(self, libros):
        self.libros = {l.id: l for l in libros}
        self.bloqueados = []

    async def get_for_update(self, libro_id):
        self.bloqueados.append(libro_id)
        return self.libros.get(libro_id)

    async def update(self, entidad):
        return entidad


class ListaFake:
    def __init__(self):
        self.items = []

    async def add(self, entidad):
        if getattr(entidad, "id", 0) is None:
            entidad.id = len(self.items) + 1
        self.items.append(entidad)
        return entidad


class ClientesFake:
    def __init__(self, clientes):
        self.clientes = {c.id: c for c in clientes}

    async def get_by_id(self, cliente_id):
        return self.clientes.get(cliente_id)

    async def obtener_por_usuario(self, usuario_id):
        return next((c for c in self.clientes.values() if c.usuario_id == usuario_id), None)


class VentasFake(ListaFake):
    def __init__(self, detalle=None):
        super().__init__()
        self.detalle = detalle
        self.paginas = []

    async def obtener_detalle(self, venta_id):
        if self.detalle is not None:
            return self.detalle
        return next((v for v in self.items if v.id == venta_id), None)

    async def listar_pagina(self, *, page, size, cliente_id=None):
        self.paginas.append(cliente_id)
        return SimpleNamespace(items=[], total=0, page=page, size=size, pages=1)


class UowFake:
    def __init__(self, *, libros=(), clientes=(), detalle=None):
        self.libros = LibrosFake(libros)
        self.movimientos = ListaFake()
        self.clientes = ClientesFake(clientes)
        self.ventas = VentasFake(detalle)
        self.confirmaciones = 0
        self.reversiones = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.confirmaciones += 1
        else:
            self.reversiones += 1

    async def rollback(self):
        self.reversiones += 1


def catalogo():
    return [
        libro(1, "Rayuela", "25000.00", 10),
        libro(3, "Ficciones", "22000.00", 8),
        libro(5, "Bestiario", "18000.00", 1),
        libro(4, "Respiración artificial", "27000.00", 3, baja=True),
    ]


def venta(cliente_id, *renglones):
    return VentaCreate(
        cliente_id=cliente_id,
        renglones=[RenglonCreate(libro_id=l, cantidad=c) for l, c in renglones],
    )


LUCIA = Cliente(id=1, nombre="Lucía Fernández", email="lucia@example.com")


@pytest.mark.anyio
async def test_venta_copia_precios_calcula_total_y_descuenta_con_movimientos():
    uow = UowFake(libros=catalogo(), clientes=[LUCIA])
    creada = await service.crear(uow, venta(1, (3, 1), (1, 2)), usuario_id=3)

    assert [r.precio_unitario for r in creada.renglones] == [Decimal("22000.00"), Decimal("25000.00")]
    assert creada.total == Decimal("72000.00")
    assert (uow.libros.libros[1].stock, uow.libros.libros[3].stock) == (8, 7)
    assert [(m.libro_id, m.cantidad, m.venta_id, m.usuario_id) for m in uow.movimientos.items] == [
        (1, -2, creada.id, 3),
        (3, -1, creada.id, 3),
    ]
    assert all(m.motivo == f"Venta #{creada.id}" for m in uow.movimientos.items)
    # Los libros se bloquean en orden de id, aunque el cuerpo venga en otro orden.
    assert uow.libros.bloqueados[:2] == [1, 3]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "datos,mensaje",
    [
        (venta(1, (1, 1), (5, 2)), "No hay stock suficiente de «Bestiario»"),
        (venta(1, (1, 1), (999, 1)), "No existe el libro con id 999"),
        (venta(1, (4, 1)), "está dado de baja"),
        (venta(999, (1, 1)), "El cliente indicado no existe"),
    ],
)
async def test_venta_rechazada_no_escribe_nada(datos, mensaje):
    uow = UowFake(libros=catalogo(), clientes=[LUCIA])
    with pytest.raises(Conflicto, match=mensaje):
        await service.crear(uow, datos, usuario_id=3)

    assert uow.ventas.items == []
    assert uow.movimientos.items == []
    assert uow.libros.libros[1].stock == 10
    assert (uow.confirmaciones, uow.reversiones) == (0, 1)


def detalle_de(cliente_usuario_id):
    cliente = Cliente(id=1, nombre="Ana Paz", email="ana@example.com", usuario_id=cliente_usuario_id)
    return SimpleNamespace(id=7, cliente=cliente, renglones=[])


@pytest.mark.anyio
@pytest.mark.parametrize("roles", [["VENDEDOR"], ["ADMIN"], ["ADMIN", "CLIENTE"]])
async def test_el_personal_ve_cualquier_venta(roles):
    uow = UowFake(detalle=detalle_de(cliente_usuario_id=None))
    usuario = Usuario(id=3, email="v@example.com", nombre="V", password_hash="x")
    assert (await service.obtener(uow, 7, usuario=usuario, roles_vigentes=roles)).id == 7


@pytest.mark.anyio
async def test_la_cliente_ve_su_venta_y_no_la_ajena():
    ana = Usuario(id=4, email="ana@example.com", nombre="Ana", password_hash="x")
    propia = UowFake(detalle=detalle_de(cliente_usuario_id=4))
    assert (await service.obtener(propia, 7, usuario=ana, roles_vigentes=["CLIENTE"])).id == 7

    ajena = UowFake(detalle=detalle_de(cliente_usuario_id=None))
    with pytest.raises(Prohibido):
        await service.obtener(ajena, 7, usuario=ana, roles_vigentes=["CLIENTE"])


@pytest.mark.anyio
async def test_venta_inexistente_es_404_antes_que_403():
    ana = Usuario(id=4, email="ana@example.com", nombre="Ana", password_hash="x")
    with pytest.raises(NoEncontrado):
        await service.obtener(UowFake(), 999, usuario=ana, roles_vigentes=["CLIENTE"])


@pytest.mark.anyio
async def test_mis_ventas_filtra_por_la_ficha_del_usuario_o_devuelve_pagina_vacia():
    ana_cliente = Cliente(id=3, nombre="Ana Paz", email="ana@example.com", usuario_id=4)
    uow = UowFake(clientes=[LUCIA, ana_cliente])
    ana = Usuario(id=4, email="ana@example.com", nombre="Ana", password_hash="x")
    await service.listar_propias(uow, ana, page=1, size=20)
    assert uow.ventas.paginas == [3]

    vendedor = Usuario(id=3, email="v@example.com", nombre="V", password_hash="x")
    vacia = await service.listar_propias(uow, vendedor, page=1, size=20)
    assert (vacia.items, vacia.total, vacia.pages) == ([], 0, 1)
    assert uow.ventas.paginas == [3]
