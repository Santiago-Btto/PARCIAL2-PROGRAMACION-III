"""Evidencia del caso C-07: el detalle de un libro y de una venta se resuelve con
un número fijo de consultas, el mismo con uno o con varios autores / renglones.

Uso (después de seed y de correr test/casos_minimos.http, que crea la venta 2 con
dos renglones en C-06):
    python -m scripts.evidencia_c07

Imprime cada SQL emitido y el total por lectura, y guarda lo mismo en
evidencia/C-07_consultas.txt (UTF-8, para que se lea bien en cualquier sistema). Usa las mismas funciones del
service que usan los endpoints GET /libros/{id} y GET /ventas/{id}.
"""

import asyncio
from pathlib import Path

from sqlalchemy import event, func, select

import app.core.modelos  # noqa: F401
from app.core.database import crear_fabrica_sesiones, crear_motor
from app.modules.libros import service as libros_service
from app.modules.ventas import service as ventas_service
from app.modules.ventas.models import RenglonVenta


SALIDA = Path("evidencia") / "C-07_consultas.txt"
lineas: list[str] = []


def mostrar(texto: str = "") -> None:
    print(texto)
    lineas.append(texto)


async def main() -> None:
    motor = crear_motor(echo=False)
    fabrica = crear_fabrica_sesiones(motor)
    consultas: list[str] = []

    @event.listens_for(motor.sync_engine, "before_cursor_execute")
    def registrar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        consultas.append(statement)

    async def medir(titulo: str, lectura) -> None:  # noqa: ANN001
        async with fabrica() as session:
            consultas.clear()
            descripcion = await lectura(session)
            mostrar()
            mostrar(f"=== {titulo}: {descripcion}")
            for numero, sql in enumerate(consultas, start=1):
                mostrar(f"--- consulta {numero}")
                mostrar(sql)
            mostrar(f">>> TOTAL: {len(consultas)} consultas")

    def detalle_libro(libro_id: int):
        async def lectura(session):
            libro = await libros_service.obtener_detalle(session, libro_id)
            return f"libro {libro_id} «{libro.titulo}» con {len(libro.autorias)} autor(es)"
        return lectura

    def detalle_venta(venta_id: int):
        async def lectura(session):
            venta = await ventas_service.obtener(session, venta_id)
            return f"venta {venta_id} con {len(venta.renglones)} renglón(es)"
        return lectura

    await medir("GET /libros/1", detalle_libro(1))
    await medir("GET /libros/5", detalle_libro(5))

    async with fabrica() as session:
        # La venta con más renglones, para comparar contra la venta 1 (un renglón).
        con_mas = await session.scalar(
            select(RenglonVenta.venta_id)
            .group_by(RenglonVenta.venta_id)
            .order_by(func.count().desc(), RenglonVenta.venta_id.desc())
            .limit(1)
        )
    await medir("GET /ventas/1", detalle_venta(1))
    if con_mas and con_mas != 1:
        await medir(f"GET /ventas/{con_mas}", detalle_venta(con_mas))
    else:
        mostrar()
        mostrar("(Ejecutá antes el caso C-06 para tener una venta con varios renglones.)")

    await motor.dispose()
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("\n".join(lineas).lstrip("\n") + "\n", encoding="utf-8")
    print(f"\nEvidencia guardada en {SALIDA}")


if __name__ == "__main__":
    asyncio.run(main())
