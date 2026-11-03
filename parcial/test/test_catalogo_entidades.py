"""Contratos de servicios del catálogo; los mocks no acreditan garantías de BD."""

import asyncio
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

import app.core.modelos  # noqa: F401 registra todas las relaciones antes de crear modelos
from app.core.errores import Conflicto, DatosInvalidos, NoEncontrado
from app.core.paginacion import Pagina
from app.core.unit_of_work import UnitOfWork


ENTIDADES = [
    ("editoriales", "Editorial", {"nombre": "Sur", "pais": "Argentina"}),
    ("generos", "Genero", {"nombre": "Narrativa"}),
    ("autores", "Autor", {"nombre": "Cortázar", "nacionalidad": "Argentina"}),
]


def contexto(modulo, clase, datos):
    service = import_module(f"app.modules.{modulo}.service")
    model = getattr(import_module(f"app.modules.{modulo}.models"), clase)
    schemas = import_module(f"app.modules.{modulo}.schemas")
    entidad = model(id=7, **datos)
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    uow = UnitOfWork(session)
    repo = SimpleNamespace(
        add=AsyncMock(return_value=entidad),
        update=AsyncMock(return_value=entidad),
        get_by_id=AsyncMock(return_value=entidad),
        count=AsyncMock(return_value=3),
        get_all=AsyncMock(return_value=[entidad]),
    )
    setattr(uow, modulo, repo)
    uow.libros = SimpleNamespace(listar_pagina=AsyncMock(), listar_autorias=AsyncMock())
    return service, schemas, entidad, repo, session, uow


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_alta_delega_persistencia_y_confirma_uow(modulo, clase, datos):
    service, schemas, entidad, repo, session, uow = contexto(modulo, clase, datos)
    payload = getattr(schemas, clase + "Create")(**datos)

    creado = asyncio.run(service.crear(uow, payload))

    assert creado is entidad
    assert repo.add.await_args.args[0].nombre == datos["nombre"]
    session.commit.assert_awaited_once()
    repo.get_by_id.assert_not_awaited()  # unicidad a cargo de la base


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
@pytest.mark.parametrize("total,page,size,esperados", [(3, 2, 2, (2, 2)), (0, 1, 20, (1, 0))])
def test_listado_pagina_y_vacio(modulo, clase, datos, total, page, size, esperados):
    service, _, entidad, repo, _, uow = contexto(modulo, clase, datos)
    repo.count.return_value = total
    repo.get_all.return_value = [entidad] if total else []

    pagina = asyncio.run(service.listar(uow, page=page, size=size))

    assert pagina.total == total
    assert (pagina.page, pagina.size, pagina.pages) == (page, size, esperados[0])
    assert pagina.items == ([entidad] if total else [])
    repo.get_all.assert_awaited_once_with(offset=esperados[1], limit=size)


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_listado_rechaza_pagina_fuera_de_rango(modulo, clase, datos):
    service, _, _, repo, session, uow = contexto(modulo, clase, datos)
    with pytest.raises(DatosInvalidos):
        asyncio.run(service.listar(uow, page=3, size=2))
    repo.get_all.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_libros_relacionados_padre_inexistente(modulo, clase, datos):
    service, _, _, repo, _, uow = contexto(modulo, clase, datos)
    repo.get_by_id.return_value = None
    with pytest.raises(NoEncontrado):
        asyncio.run(service.listar_libros(uow, 999, page=1, size=20))
    uow.libros.listar_pagina.assert_not_awaited()
    uow.libros.listar_autorias.assert_not_awaited()


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES[:2])
def test_libros_relacionados_reutilizan_filtro_y_pagina(modulo, clase, datos):
    service, _, _, _, _, uow = contexto(modulo, clase, datos)
    esperado = Pagina(items=[], total=0, page=1, size=5, pages=1)
    uow.libros.listar_pagina.return_value = esperado

    pagina = asyncio.run(service.listar_libros(uow, 7, page=1, size=5))

    assert pagina is esperado
    filtro = "editorial_id" if modulo == "editoriales" else "genero_id"
    uow.libros.listar_pagina.assert_awaited_once_with(page=1, size=5, **{filtro: 7})


def test_libros_de_autor_conserva_rol_orden_y_metadatos():
    service, _, _, _, _, uow = contexto(*ENTIDADES[2])
    libro = SimpleNamespace(isbn="978-950-49-0385-8", titulo="Rayuela", precio=Decimal("15.00"))
    autoria = SimpleNamespace(libro_id=13, libro=libro, rol="traductor", orden=2)
    uow.libros.listar_autorias.return_value = Pagina(
        items=[autoria], total=3, page=2, size=1, pages=3
    )

    pagina = asyncio.run(service.listar_libros(uow, 7, page=2, size=1))

    assert (pagina.total, pagina.page, pagina.size, pagina.pages) == (3, 2, 1, 3)
    assert pagina.items[0].model_dump() == {
        "libro_id": 13, "isbn": libro.isbn, "titulo": "Rayuela", "precio": Decimal("15.00"),
        "rol": "traductor", "orden": 2,
    }


@pytest.mark.parametrize("modulo,clase,datos", [ENTIDADES[0], ENTIDADES[2]])
def test_patch_conserva_omitidos_y_rechaza_inexistente(modulo, clase, datos):
    service, schemas, entidad, repo, _, uow = contexto(modulo, clase, datos)
    payload = getattr(schemas, clase + "Update")(nombre="Nuevo nombre")

    asyncio.run(service.actualizar(uow, 7, payload))

    repo.update.assert_awaited_once_with(entidad, {"nombre": "Nuevo nombre"})
    repo.get_by_id.return_value = None
    with pytest.raises(NoEncontrado):
        asyncio.run(service.actualizar(uow, 404, payload))


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES[:2])
@pytest.mark.parametrize("en_commit", [False, True])
def test_conflicto_revierte_tambien_si_falla_commit(modulo, clase, datos, en_commit):
    service, schemas, _, repo, session, uow = contexto(modulo, clase, datos)
    nombre = "uq_editorial_nombre" if modulo == "editoriales" else "uq_genero_nombre"
    original = Exception("Detalle privado SQL")
    original.constraint_name = nombre
    fallo = IntegrityError("SQL privado", {}, original)
    if en_commit:
        session.commit.side_effect = fallo
    else:
        repo.add.side_effect = fallo

    with pytest.raises(Conflicto) as capturado:
        asyncio.run(service.crear(uow, getattr(schemas, clase + "Create")(**datos)))

    assert "Ya existe" in capturado.value.mensaje
    assert "privado" not in capturado.value.mensaje
    assert session.rollback.await_count >= 1


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_entradas_estrictas_y_nulos_patch(modulo, clase, datos):
    _, schemas, _, _, _, _ = contexto(modulo, clase, datos)
    create = getattr(schemas, clase + "Create")
    with pytest.raises(ValidationError):
        create(**datos, inesperado=True)
    if modulo != "generos":
        patch = getattr(schemas, clase + "Update")
        with pytest.raises(ValidationError):
            patch(nombre=None)
        with pytest.raises(ValidationError):
            patch(inesperado=True)


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_uow_compone_repositorios_y_solo_confirma_al_salir(modulo, clase, datos):
    uow_module = import_module(f"app.modules.{modulo}.unit_of_work")
    uow_class = getattr(uow_module, modulo.capitalize() + "UnitOfWork")
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    uow = uow_class(session)
    entidad = getattr(import_module(f"app.modules.{modulo}.models"), clase)(id=1, **datos)

    async def alta():
        async with uow:
            await getattr(uow, modulo).add(entidad)
            session.commit.assert_not_awaited()
        assert uow.libros.session is session

    asyncio.run(alta())

    session.add.assert_called_once_with(entidad)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.close.assert_not_called()


@pytest.mark.parametrize("modulo,clase,datos", ENTIDADES)
def test_routers_separan_lecturas_y_escrituras(modulo, clase, datos):
    routing = import_module(f"app.modules.{modulo}.router")
    publicas = {metodo for ruta in routing.router_publico.routes for metodo in ruta.methods}
    protegidas = {metodo for ruta in routing.router_protegido.routes for metodo in ruta.methods}
    assert publicas == {"GET"}
    assert protegidas == ({"POST"} if modulo == "generos" else {"POST", "PATCH"})
    assert routing.router_protegido.dependencies
