# Handoff C-03 → C-04: stock de libros

C-03 expone `app.modules.libros.stock.cambiar_stock` para que la venta actualice
stock y agregue `MovimientoStock` dentro de la misma transacción.

```python
await cambiar_stock(
    uow,
    libro_id=libro.id,
    cantidad=-cantidad_vendida,
    usuario_id=usuario_actual.id,
    motivo=f"Venta #{venta.id}",
    venta_id=venta.id,
)
```

`uow` debe ofrecer `libros.get_for_update`, `libros.update` y
`movimientos.add` sobre una única sesión; el `VentasUnitOfWork` de C-04 puede
componer esos repositorios. El llamador abre y confirma/revierte el UoW. El
helper no confirma por su cuenta, rechaza stock insuficiente, libro dado de baja,
variaciones inválidas y overflow de `INTEGER`; inserta un movimiento con el actor
y la venta. El repositorio refresca la fila bajo `SELECT FOR UPDATE`, así que
varias operaciones concurrentes no pierden incrementos.

Al vender varios libros, validá todos antes de confirmar la venta y procesá los
bloqueos en orden estable por `libro_id`; si cualquier renglón o movimiento falla,
dejá propagar el error para que el UoW revierta toda la venta. Rechazá libros
repetidos en el payload.

Todavía corresponde a C-04 reemplazar la escritura directa de `Libro.stock` en
`ventas/service.py` y `seed.py`. Hasta esa migración, `RN-11` y `RN-13` no están
garantizadas globalmente por el sistema ni se debe anunciar la igualdad total
entre stock y suma de movimientos como una propiedad global.

Para una venta histórica, cargar `Libro` y movimientos por identificador sin
filtrar `borrado_en`: la baja lógica oculta el libro del catálogo, pero conserva
su stock, relaciones e historial para el detalle de la venta.

La reproducción real de C-02 confirmó que `sqlalchemy.select` con
`AsyncSession.exec` devolvía filas `Row` en vez de modelos/valores escalares,
rompiendo la búsqueda del usuario y la lectura de roles. Con autorización
posterior del dueño, C-02 quedó corregido en el commit
`e2de62c fix(auth): devuelve valores escalares desde SQLModel`: los dos imports
usan `sqlmodel.select`, con regresiones unitarias para usuario, roles y lista
vacía de roles.

Después del arreglo pasaron 95 pruebas unitarias de auth y catálogo; la suite
completa sin PostgreSQL dio 116 pasadas y 22 omitidas por requerir PostgreSQL
16. La suite integrada C-03 ya había dado 135/135 antes del arreglo, con auth
aislada mediante overrides. En la sesión posterior no fue posible reabrir el
PostgreSQL local porque Windows denegó el bind de loopback; queda pendiente
repetir el login y la autorización ADMIN end-to-end con PostgreSQL disponible.
El cambio de C-02 es acotado y no modifica el contrato `cambiar_stock`.

## Cierre en C-04

C-04 consumió este contrato tal como está descripto: `VentasUnitOfWork` compone
`libros` y `movimientos`, la venta valida y bloquea los libros en orden de id antes
de escribir, y cada renglón descuenta por `cambiar_stock` con `venta_id`. `seed.py`
tampoco escribe `Libro.stock` directamente: carga cada stock inicial por el mismo
helper y registra la venta 1 con `ventas.service.crear`. Desde C-04 no queda ninguna
escritura de stock fuera del punto único, y RN-11 vale para todo el sistema.
