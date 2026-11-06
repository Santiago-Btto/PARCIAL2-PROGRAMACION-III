"""Comportamientos de catálogo sobre PostgreSQL 16 y esquema Alembic real."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlmodel import select

from catalogo_db import anyio_backend, database_url, db_factory  # noqa: F401
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.libros.schemas import LibroDetalle
from app.modules.autores.models import Autor
from app.modules.generos.models import Genero
from app.modules.libros.models import LibroAutor
from app.core.errores import DatosInvalidos
from app.core.errores import Conflicto, NoEncontrado
from app.modules.libros import service
from app.modules.libros.schemas import LibroCreate, LibroUpdate, ReposicionCreate
from app.modules.libros.service import cambiar_stock
from app.modules.usuarios.models import Usuario
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import Venta
from app.modules.libros.models import MovimientoStock
from sqlalchemy import func
import asyncio
from sqlalchemy import event

pytestmark = pytest.mark.anyio


async def test_repositorio_base_entrega_entidades_y_pagina_real(db_factory):
    async with db_factory() as session:
        primera = Editorial(nombre="Primera", pais="AR")
        segunda = Editorial(nombre="Segunda", pais="UY")
        session.add_all([primera, segunda])
        await session.commit()
        repo = BaseRepository(session, Editorial)
        obtenida = await repo.get_by_id(primera.id)
        assert obtenida.nombre == "Primera"
        assert await repo.get_by_id(999999) is None
        items = await repo.get_all(offset=1, limit=1)
        assert [item.nombre for item in items] == ["Segunda"]
        assert await repo.count() == 2


async def test_soft_repository_filtra_y_conserva_historico(db_factory):
    async with db_factory() as session:
        editorial = Editorial(nombre="Primera", pais="AR")
        session.add(editorial)
        await session.flush()
        vigente = Libro(isbn="978-950-000001-1", titulo="Vigente", precio=Decimal("10"), editorial_id=editorial.id)
        baja = Libro(isbn="978-950-000002-8", titulo="Baja", precio=Decimal("12"), editorial_id=editorial.id,
                     borrado_en=datetime.now(UTC))
        session.add_all([vigente, baja])
        await session.commit()
        repo = SoftDeleteRepository(session, Libro)
        assert (await repo.get_by_id(vigente.id)).titulo == "Vigente"
        assert await repo.get_by_id(baja.id) is None
        assert [libro.titulo for libro in await repo.get_all()] == ["Vigente"]
        assert await repo.count() == 1
        historico = await repo.get_by_id_including_deleted(baja.id)
        assert historico.titulo == "Baja"
        assert historico.borrado_en.tzinfo is not None


async def cargar_catalogo(factory, titulos=("Rayuela",), *, autores=2):
    async with factory() as session:
        editorial = Editorial(nombre="Editorial", pais="AR")
        genero = Genero(nombre="Novela")
        otros = Genero(nombre="Ensayo")
        autores_datos = [Autor(nombre=f"Autor {n}", nacionalidad="AR") for n in range(autores)]
        session.add_all([editorial, genero, otros, *autores_datos])
        await session.flush()
        libros = []
        for n, titulo in enumerate(titulos):
            libro = Libro(isbn=f"978950{n:07d}", titulo=titulo, precio=Decimal("12.50"),
                          editorial_id=editorial.id, genero_id=genero.id)
            libro.autorias = [LibroAutor(autor_id=a.id, rol="autor" if i == 0 else "coautor", orden=i+1)
                              for i, a in enumerate(autores_datos)]
            session.add(libro)
            libros.append(libro)
        await session.commit()
        return editorial.id, genero.id, otros.id, [a.id for a in autores_datos], [libro.id for libro in libros]


async def test_libro_repository_precarga_detalle_y_comparte_sesion(db_factory):
    _, _, _, autores, libros = await cargar_catalogo(db_factory, autores=4)
    async with db_factory() as session:
        uow = LibrosUnitOfWork(session)
        assert uow.libros.session is uow.movimientos.session is session
        libro = await uow.libros.obtener_detalle(libros[0])
        detalle = LibroDetalle.desde(libro)
        assert detalle.editorial.nombre == "Editorial"
        assert detalle.genero.nombre == "Novela"
        assert [a.autor_id for a in detalle.autores] == autores
        assert [a.orden for a in detalle.autores] == [1, 2, 3, 4]
        assert await uow.libros.obtener_detalle(999999) is None


@pytest.mark.parametrize("cantidad_autores", [1, 4])
async def test_detalle_usa_numero_fijo_de_consultas(db_factory, cantidad_autores):
    await cargar_catalogo(db_factory, autores=cantidad_autores)
    consultas = []
    async with db_factory() as session:
        def contar_select(_connection, _cursor, sentencia, _parametros, _contexto, _muchos):
            if sentencia.lstrip().upper().startswith("SELECT"):
                consultas.append(sentencia)

        event.listen(session.bind.sync_engine, "before_cursor_execute", contar_select)
        try:
            libro = await LibroRepository(session).obtener_detalle(1)
            assert len(libro.autorias) == cantidad_autores
        finally:
            event.remove(session.bind.sync_engine, "before_cursor_execute", contar_select)
    assert len(consultas) == 2


async def test_libro_repository_pagina_y_filtros_coherentes(db_factory):
    _, genero, otro, _, libros = await cargar_catalogo(db_factory, tuple(f"Libro {n}" for n in range(25)))
    async with db_factory() as session:
        repo = LibroRepository(session)
        pagina = await repo.listar_pagina(page=2, size=20, titulo="lIbRo", genero_id=genero)
        assert (pagina.total, pagina.page, pagina.pages) == (25, 2, 2)
        assert [libro.id for libro in pagina.items] == libros[20:]
        vacia = await repo.listar_pagina(page=1, size=20, genero_id=otro)
        assert (vacia.items, vacia.total, vacia.pages) == ([], 0, 1)
        with pytest.raises(DatosInvalidos):
            await repo.listar_pagina(page=3, size=20)


@pytest.mark.parametrize("texto", ["100%", "cap_1", "a\\b", "' OR '1'='1"])
async def test_libro_repository_busca_texto_literal(db_factory, texto):
    await cargar_catalogo(db_factory, (f"Contiene {texto}", "Sin coincidencia", "1000 capX1 axb"))
    async with db_factory() as session:
        pagina = await LibroRepository(session).listar_pagina(page=1, size=20, titulo=texto)
        assert [libro.titulo for libro in pagina.items] == [f"Contiene {texto}"]
        assert pagina.total == 1


async def test_relacionados_excluyen_bajas_y_conservan_rol_orden(db_factory):
    editorial, genero, _, autores, libros = await cargar_catalogo(db_factory, ("Vigente", "Baja"))
    async with db_factory() as session:
        repo = LibroRepository(session)
        await repo.soft_delete(await repo.get_by_id(libros[1]))
        await session.commit()
        for filtro in ({"editorial_id": editorial}, {"genero_id": genero}):
            pagina = await repo.listar_pagina(page=1, size=20, **filtro)
            assert [libro.id for libro in pagina.items] == [libros[0]]
            assert pagina.total == 1
        autorias = await repo.listar_autorias(autores[1], page=1, size=20)
        assert [(a.libro.titulo, a.rol, a.orden) for a in autorias.items] == [("Vigente", "coautor", 2)]
        assert autorias.total == 1
        assert await repo.obtener_detalle(libros[1]) is None
        assert (await repo.get_by_id_including_deleted(libros[1])).titulo == "Baja"


async def preparar_alta(factory):
    editorial, genero, _, autores, _ = await cargar_catalogo(factory, ())
    async with factory() as session:
        usuario = Usuario(email="admin-catalogo@example.test", nombre="Admin catálogo", password_hash="sintético")
        session.add(usuario)
        await session.commit()
        return editorial, genero, autores, usuario.id


def alta(editorial, genero, autores, *, stock=0, isbn="978-950-100001-1"):
    return LibroCreate(
        isbn=isbn, titulo="Nuevo libro", precio=Decimal("125.50"), stock_inicial=stock,
        editorial_id=editorial, genero_id=genero,
        autores=[{"autor_id": autor_id, "rol": "autor" if n == 0 else "coautor", "orden": n+1}
                 for n, autor_id in enumerate(autores)],
    )


@pytest.mark.parametrize("stock", [0, 7])
async def test_alta_stock_y_autorias_son_atomicos(db_factory, stock):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        libro = await service.crear(LibrosUnitOfWork(session), alta(editorial, genero, autores, stock=stock), usuario_id=actor)
        assert libro.stock == stock
        assert [a.autor_id for a in libro.autorias] == autores
        movimientos = list((await session.exec(select(MovimientoStock))).all())
        assert [m.cantidad for m in movimientos] == ([stock] if stock else [])
        assert sum(m.cantidad for m in movimientos) == libro.stock
        if stock:
            assert (movimientos[0].usuario_id, movimientos[0].venta_id, movimientos[0].motivo) == (actor, None, "Stock inicial")


@pytest.mark.parametrize("referencia", ["autor", "editorial"])
async def test_alta_referencia_invalida_revierte_todo(db_factory, referencia):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    datos = alta(999999 if referencia == "editorial" else editorial, genero,
                 [999999] if referencia == "autor" else autores, stock=7)
    async with db_factory() as session:
        with pytest.raises(Conflicto):
            await service.crear(LibrosUnitOfWork(session), datos, usuario_id=actor)
        assert await session.scalar(select(func.count()).select_from(Libro)) == 0
        assert await session.scalar(select(func.count()).select_from(LibroAutor)) == 0
        assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 0


async def test_patch_conserva_stock_y_refresca_relaciones(db_factory):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        uow = LibrosUnitOfWork(session)
        libro = await service.crear(uow, alta(editorial, genero, autores, stock=5), usuario_id=actor)
        actualizado = await service.actualizar(uow, libro.id, LibroUpdate(titulo="Editado", genero_id=None))
        assert (actualizado.titulo, actualizado.genero, actualizado.stock) == ("Editado", None, 5)
        assert actualizado.isbn == libro.isbn
        assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 1


async def test_baja_libera_isbn_y_preserva_historial_por_identificador(db_factory):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        uow = LibrosUnitOfWork(session)
        libro = await service.crear(uow, alta(editorial, genero, autores, stock=7), usuario_id=actor)
        original_id = libro.id
        await service.reponer(uow, original_id, ReposicionCreate(cantidad=3, motivo="Compra"), usuario_id=actor)
        await service.eliminar(uow, original_id)
        with pytest.raises(NoEncontrado):
            await service.obtener_detalle(uow, original_id)
        with pytest.raises(NoEncontrado):
            await service.eliminar(uow, original_id)
        with pytest.raises(Conflicto):
            await service.reponer(uow, original_id, ReposicionCreate(cantidad=1, motivo="Compra"), usuario_id=actor)
        nuevo = await service.crear(uow, alta(editorial, genero, autores, stock=2), usuario_id=actor)
        assert nuevo.id != original_id
        nuevo_id = nuevo.id
        with pytest.raises(Conflicto, match="ISBN"):
            await service.crear(uow, alta(editorial, genero, autores, stock=2), usuario_id=actor)
        historico = await service.listar_movimientos(uow, original_id, page=1, size=1)
        assert (historico.total, historico.pages) == (2, 2)
        assert [m.cantidad for m in historico.items] == [7]
        pagina2 = await service.listar_movimientos(uow, original_id, page=2, size=1)
        assert [m.cantidad for m in pagina2.items] == [3]
        assert all(m.libro_id == original_id for m in [*historico.items, *pagina2.items])
        assert [m.cantidad for m in (await service.listar_movimientos(uow, nuevo_id, page=1, size=20)).items] == [2]
        assert (await uow.libros.get_by_id_including_deleted(original_id)).borrado_en.tzinfo is not None


async def test_reposicion_fallida_no_deja_stock_sin_movimiento(db_factory):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        uow = LibrosUnitOfWork(session)
        libro = await service.crear(uow, alta(editorial, genero, autores, stock=4), usuario_id=actor)
        libro_id = libro.id
        with pytest.raises(Conflicto):
            await service.reponer(uow, libro_id, ReposicionCreate(cantidad=3, motivo="Actor inválido"), usuario_id=999999)
        assert (await session.get(Libro, libro_id)).stock == 4
        assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 1


async def test_helper_negativo_participa_en_uow_y_rollback_del_llamador(db_factory):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        libro = await service.crear(LibrosUnitOfWork(session), alta(editorial, genero, autores, stock=5), usuario_id=actor)
        libro_id = libro.id
        cliente = Cliente(nombre="Cliente sintético", email="cliente-catalogo@example.test")
        session.add(cliente)
        await session.flush()
        venta = Venta(cliente_id=cliente.id, total=Decimal("0"))
        session.add(venta)
        await session.commit()
        venta_id = venta.id
        async with LibrosUnitOfWork(session) as uow:
            await cambiar_stock(uow, libro_id=libro_id, cantidad=-2, usuario_id=actor, motivo="Venta sintética", venta_id=venta_id)
        assert (await session.get(Libro, libro_id)).stock == 3
        movimiento = (await session.exec(select(MovimientoStock).where(MovimientoStock.cantidad == -2))).one()
        assert movimiento.venta_id == venta_id
        with pytest.raises(RuntimeError):
            async with LibrosUnitOfWork(session) as uow:
                await cambiar_stock(uow, libro_id=libro_id, cantidad=8, usuario_id=actor, motivo="Se revierte")
                raise RuntimeError("Falla posterior del llamador")
        assert (await session.get(Libro, libro_id)).stock == 3
        assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 2


async def test_reposiciones_concurrentes_no_pierden_incrementos(db_factory):
    editorial, genero, autores, actor = await preparar_alta(db_factory)
    async with db_factory() as session:
        libro = await service.crear(LibrosUnitOfWork(session), alta(editorial, genero, autores, stock=4), usuario_id=actor)
        libro_id = libro.id
    comenzar = asyncio.Event()
    async def reponer(cantidad):
        async with db_factory() as session:
            # Precarga intencional: el helper debe refrescar la identidad bajo el lock.
            await session.get(Libro, libro_id)
            await comenzar.wait()
            return await service.reponer(LibrosUnitOfWork(session), libro_id,
                                         ReposicionCreate(cantidad=cantidad, motivo=f"Compra {cantidad}"), usuario_id=actor)
    tareas = [asyncio.create_task(reponer(n)) for n in (2, 3)]
    comenzar.set()
    await asyncio.wait_for(asyncio.gather(*tareas), timeout=10)
    async with db_factory() as session:
        assert (await session.get(Libro, libro_id)).stock == 9
        assert sorted((await session.exec(select(MovimientoStock.cantidad))).all()) == [2, 3, 4]


async def test_servicio_listado_usa_uow_y_pagina_publica(db_factory):
    await cargar_catalogo(db_factory, ("Libro 1", "Libro 2"))
    async with db_factory() as session:
        pagina = await service.listar(LibrosUnitOfWork(session), page=2, size=1)
        assert (pagina.total, pagina.pages, [libro.titulo for libro in pagina.items]) == (2, 2, ["Libro 2"])
