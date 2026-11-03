"""Rutas HTTP públicas y protegidas del catálogo."""

from httpx import ASGITransport, AsyncClient
from fastapi import Request
import pytest

from app.main import app
from app.core.database import get_session
from app.core.dependencies import get_roles_vigentes, get_usuario_actual
from app.core.errores import NoAutenticado
from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.usuarios.models import Usuario
from catalogo_db import database_url, db_factory  # noqa: F401

pytestmark = pytest.mark.anyio


def test_catalogo_publico_y_administrativo_montados():
    metodos = {(ruta.path, metodo) for ruta in app.routes for metodo in getattr(ruta, "methods", ())}
    assert ("/libros/", "GET") in metodos
    assert ("/libros/", "POST") in metodos
    assert ("/libros/{libro_id}/reponer", "POST") in metodos
    assert ("/libros/{libro_id}/movimientos", "GET") in metodos
    assert ("/editoriales/", "GET") in metodos
    assert ("/editoriales/", "POST") in metodos


async def test_http_catalogo_pagina_permisos_stock_y_baja(db_factory):
    async with db_factory() as session:
        editorial = Editorial(nombre="HTTP", pais="AR")
        genero = Genero(nombre="Narrativa HTTP")
        autor = Autor(nombre="Autora HTTP", nacionalidad="AR")
        usuario = Usuario(
            email="http-catalogo@example.test", nombre="Admin HTTP", password_hash="sintético"
        )
        session.add_all([editorial, genero, autor, usuario])
        await session.commit()
        editorial_id, genero_id, autor_id = editorial.id, genero.id, autor.id
        usuario_id = usuario.id

    async def session_override():
        async with db_factory() as session:
            yield session

    async def usuario_override(request: Request):
        if request.headers.get("x-test-user") != "yes":
            raise NoAutenticado("No hay sesión iniciada.")
        async with db_factory() as session:
            usuario = await session.get(Usuario, usuario_id)
            if request.headers.get("x-test-change") == "yes":
                usuario.debe_cambiar_password = True
            return usuario

    async def roles_override(request: Request):
        return ["ADMIN"] if request.headers.get("x-test-role") == "admin" else []

    originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_usuario_actual] = usuario_override
    app.dependency_overrides[get_roles_vigentes] = roles_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            lista = await client.get("/libros/?page=1&size=5")
            assert lista.status_code == 200
            assert lista.json() == {"items": [], "total": 0, "page": 1, "size": 5, "pages": 1}
            titulo_vacio = await client.get("/libros/?titulo=&page=1&size=5")
            assert titulo_vacio.status_code == 422

            sin_sesion = await client.post("/libros/", json={})
            assert sin_sesion.status_code == 401
            sin_rol = await client.post("/libros/", headers={"x-test-user": "yes"}, json={})
            assert sin_rol.status_code == 403
            clave_pendiente = await client.get(
                "/libros/1/movimientos",
                headers={"x-test-user": "yes", "x-test-role": "admin", "x-test-change": "yes"},
            )
            assert clave_pendiente.status_code == 403

            headers = {"x-test-user": "yes", "x-test-role": "admin"}
            payload = {
                "isbn": "978-950-100001-1", "titulo": "Alta HTTP", "precio": "125.50",
                "stock_inicial": 4, "editorial_id": editorial_id, "genero_id": genero_id,
                "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}],
            }
            alta = await client.post("/libros/", headers=headers, json=payload)
            assert alta.status_code == 201
            libro = alta.json()
            assert libro["stock"] == 4
            libro_id = libro["id"]

            patch_stock = await client.patch(f"/libros/{libro_id}", headers=headers, json={"stock": 9})
            assert patch_stock.status_code == 422
            reposicion = await client.post(
                f"/libros/{libro_id}/reponer", headers=headers,
                json={"cantidad": 3, "motivo": "Compra"},
            )
            assert (reposicion.status_code, reposicion.json()["stock"]) == (200, 7)

            baja = await client.delete(f"/libros/{libro_id}", headers=headers)
            assert baja.status_code == 204 and baja.content == b""
            assert (await client.get(f"/libros/{libro_id}")).status_code == 404
            movimientos = await client.get(f"/libros/{libro_id}/movimientos", headers=headers)
            assert movimientos.status_code == 200
            assert [m["cantidad"] for m in movimientos.json()["items"]] == [4, 3]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originales)
