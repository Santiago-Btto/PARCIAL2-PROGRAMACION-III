"""Evidencia del caso C-15: el detalle de una venta se resuelve con un número fijo
de consultas, el mismo con 2 que con 4 renglones.

Uso (después de `python seed.py` y de correr el caso C-15 de
test/04_clientes_y_ventas.http, que registra una venta con 4 renglones):
    python -m scripts.evidencia_c15

Usa el mismo método del repositorio que el endpoint GET /ventas/{id}
(`VentaRepository.obtener_detalle`), muestra cada SQL emitido y el total por
lectura, y guarda lo mismo en evidencia/C-15_consultas.txt (UTF-8).
"""

import asyncio
from pathlib import Path

from sqlalchemy import event, func, select

import app.core.modelos  # noqa: F401
from app.core.database import crear_fabrica_sesiones, crear_motor
from app.modules.ventas.models import RenglonVenta
from app.modules.ventas.repository import VentaRepository

SALIDA = Path("evidencia") / "C-15_consultas.txt"
lineas: list[str] = []


def mostrar(texto: str = "") -> None:
    print(texto)
    lineas.append(texto)


async def venta_con_renglones(fabrica, cantidad: int) -> int | None:  # noqa: ANN001
    async with fabrica() as session:
        return await session.scalar(
            select(RenglonVenta.venta_id)
            .group_by(RenglonVenta.venta_id)
            .having(func.count() == cantidad)
            .order_by(RenglonVenta.venta_id)
            .limit(1)
        )


async def main() -> None:
    motor = crear_motor(echo=False)
    fabrica = crear_fabrica_sesiones(motor)
    consultas: list[str] = []

    @event.listens_for(motor.sync_engine, "before_cursor_execute")
    def registrar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        consultas.append(statement)

    totales: dict[int, int] = {}
    for cantidad in (2, 4):
        venta_id = await venta_con_renglones(fabrica, cantidad)
        mostrar()
        if venta_id is None:
            mostrar(f"(No hay una venta con {cantidad} renglones: correr antes el caso C-15.)")
            continue
        async with fabrica() as session:
            consultas.clear()
            venta = await VentaRepository(session).obtener_detalle(venta_id)
            titulos = ", ".join(r.libro.titulo for r in venta.renglones)  # type: ignore[union-attr]
            mostrar(f"=== GET /ventas/{venta_id}: {len(venta.renglones)} renglones ({titulos})")  # type: ignore[union-attr]
            for numero, sql in enumerate(consultas, start=1):
                mostrar(f"--- consulta {numero}")
                mostrar(sql)
            mostrar(f">>> TOTAL: {len(consultas)} consultas")
            totales[cantidad] = len(consultas)

    if len(totales) == 2:
        mostrar()
        iguales = "iguales" if totales[2] == totales[4] else "DISTINTAS"
        mostrar(f"Resultado: 2 renglones -> {totales[2]} consultas; "
                f"4 renglones -> {totales[4]} consultas ({iguales}).")

    await motor.dispose()
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("\n".join(lineas).lstrip("\n") + "\n", encoding="utf-8")
    print(f"\nEvidencia guardada en {SALIDA}")


if __name__ == "__main__":
    asyncio.run(main())
