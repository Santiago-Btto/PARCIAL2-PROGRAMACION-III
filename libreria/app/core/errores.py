"""Errores de dominio y traducción de IntegrityError a mensajes propios (RN-12).

Los services lanzan NoEncontrado / Conflicto; main.py los convierte en 404 / 409.
El texto original de la base (tablas, restricciones, trazas) solo va al log del
servidor, nunca a la respuesta.
"""

import logging
from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("libreria.errores")


class ErrorDominio(Exception):
    status_code = 400

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorDominio):
    status_code = 404


class Conflicto(ErrorDominio):
    status_code = 409


# Nombre de restricción -> (tipo de error, mensaje para el cliente)
MapaRestricciones = Mapping[str, tuple[type[ErrorDominio], str]]

_GENERICOS_POR_SQLSTATE = {
    "23505": "Ya existe un registro con esos datos.",
    "23503": "Alguno de los datos hace referencia a un recurso que no existe.",
    "23514": "Alguno de los valores no cumple las reglas de negocio.",
    "23502": "Falta un dato obligatorio.",
}


def _diagnostico(exc: IntegrityError) -> tuple[str | None, str | None]:
    """Devuelve (sqlstate, nombre de la restricción) del error de asyncpg.

    SQLAlchemy envuelve la excepción de asyncpg; la original queda en __cause__
    y trae los atributos sqlstate y constraint_name.
    """
    sqlstate: str | None = None
    restriccion: str | None = None
    for candidato in (exc.orig, getattr(exc.orig, "__cause__", None)):
        if candidato is None:
            continue
        sqlstate = sqlstate or getattr(candidato, "sqlstate", None)
        restriccion = restriccion or getattr(candidato, "constraint_name", None)
    return sqlstate, restriccion


def traducir_integrity_error(exc: IntegrityError, mapa: MapaRestricciones) -> ErrorDominio:
    sqlstate, restriccion = _diagnostico(exc)
    logger.info("IntegrityError traducido: sqlstate=%s restriccion=%s", sqlstate, restriccion)
    if restriccion and restriccion in mapa:
        tipo, mensaje = mapa[restriccion]
        return tipo(mensaje)
    return Conflicto(
        _GENERICOS_POR_SQLSTATE.get(
            sqlstate or "", "La operación no respeta una regla de integridad de los datos."
        )
    )
