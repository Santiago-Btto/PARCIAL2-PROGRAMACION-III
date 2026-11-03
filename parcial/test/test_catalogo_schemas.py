"""Contratos de entrada de C-03: datos válidos y rechazos sin persistencia."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.parametros import MAX_ID
from app.modules.autores.schemas import AutorCreate, AutorUpdate
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.schemas import AutoriaCreate, LibroCreate, LibroUpdate, ReposicionCreate


def libro_valido(**cambios):
    return {
        "isbn": "978-950-000001-1",
        "titulo": "Libro de prueba",
        "precio": "120.50",
        "editorial_id": 1,
        "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}],
        **cambios,
    }


@pytest.mark.parametrize("schema,datos", [
    (EditorialCreate, {"nombre": "Editorial", "pais": "AR"}),
    (EditorialUpdate, {"pais": "UY"}),
    (GeneroCreate, {"nombre": "Novela"}),
    (AutorCreate, {"nombre": "Autora", "nacionalidad": "AR"}),
    (AutorUpdate, {"nombre": "Autora editada"}),
    (AutoriaCreate, {"autor_id": 1, "rol": "autor", "orden": 1}),
    (LibroCreate, libro_valido()),
    (LibroUpdate, {"titulo": "Título editado"}),
    (ReposicionCreate, {"cantidad": 2, "motivo": "Compra"}),
])
def test_entradas_rechazan_campos_desconocidos(schema, datos):
    with pytest.raises(ValidationError):
        schema.model_validate({**datos, "campo_desconocido": "no aceptar"})


@pytest.mark.parametrize("stock", [0, 7, MAX_ID])
def test_alta_acepta_stock_inicial(stock):
    assert LibroCreate.model_validate(libro_valido(stock_inicial=stock)).stock_inicial == stock


def test_alta_omite_stock_inicial_y_empieza_sin_existencias():
    assert LibroCreate.model_validate(libro_valido()).stock_inicial == 0


@pytest.mark.parametrize("cambios", [
    {"stock": 1}, {"stock_inicial": -1}, {"stock_inicial": MAX_ID + 1},
    {"precio": "0"}, {"isbn": "inválido"},
    {"autores": [{"autor_id": 1, "rol": "autor", "orden": 1, "extra": True}]},
    {"autores": [{"autor_id": 1, "rol": "autor", "orden": 1},
                 {"autor_id": 1, "rol": "coautor", "orden": 2}]},
    {"autores": [{"autor_id": 1, "rol": "autor", "orden": 1},
                 {"autor_id": 2, "rol": "coautor", "orden": 1}]},
])
def test_alta_rechaza_stock_invalido_y_conserva_validaciones(cambios):
    with pytest.raises(ValidationError):
        LibroCreate.model_validate(libro_valido(**cambios))


@pytest.mark.parametrize("campo", ["stock", "stock_inicial"])
def test_patch_no_admite_existencias(campo):
    with pytest.raises(ValidationError):
        LibroUpdate.model_validate({campo: 2})


def test_patch_conserva_campos_omitidos_y_permite_quitar_genero():
    assert LibroUpdate(titulo="Otro").model_dump(exclude_unset=True) == {"titulo": "Otro"}
    assert LibroUpdate(genero_id=None).model_dump(exclude_unset=True) == {"genero_id": None}
    assert LibroUpdate(isbn="978-950-000002-8", editorial_id=2).model_dump(exclude_unset=True) == {
        "isbn": "978-950-000002-8", "editorial_id": 2,
    }


@pytest.mark.parametrize("schema,campo", [
    (EditorialUpdate, "pais"), (AutorUpdate, "nombre"),
    (LibroUpdate, "precio"), (LibroUpdate, "titulo"), (LibroUpdate, "editorial_id"),
])
def test_patch_rechaza_nulo_explicito_obligatorio(schema, campo):
    with pytest.raises(ValidationError):
        schema.model_validate({campo: None})


@pytest.mark.parametrize("datos", [
    {"cantidad": 0, "motivo": "Compra"}, {"cantidad": -1, "motivo": "Compra"},
    {"cantidad": MAX_ID + 1, "motivo": "Compra"},
    {"cantidad": 1, "motivo": ""}, {"cantidad": 1, "motivo": "   "},
    {"cantidad": 1, "motivo": "x" * 201},
])
def test_reposicion_rechaza_datos_invalidos(datos):
    with pytest.raises(ValidationError):
        ReposicionCreate.model_validate(datos)


@pytest.mark.parametrize("cantidad,motivo", [(1, "Compra"), (MAX_ID, " Ajuste ")])
def test_reposicion_valida_y_normaliza_motivo(cantidad, motivo):
    datos = ReposicionCreate(cantidad=cantidad, motivo=motivo)
    assert (datos.cantidad, datos.motivo) == (cantidad, motivo.strip())
