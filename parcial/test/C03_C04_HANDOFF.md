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

La reproducción real de C-02 confirmó un defecto anterior de `sqlalchemy.select`
con `AsyncSession.exec` en las consultas de autenticación/RBAC. El dueño del
trabajo decidió mantener C-03 acotado; C-04 deberá considerar esa limitación y
no asumir que este cambio arregla el login o la lectura real de roles.
