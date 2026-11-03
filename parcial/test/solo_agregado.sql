-- Caso C-14 (Ejercicio 7, RN-12):
-- Demuestra que el disparador `trg_movimiento_stock_solo_agregado` instalado
-- en la cuarta migración rechaza cualquier UPDATE o DELETE sobre `movimiento_stock`,
-- venga de donde venga (incluida una sesión directa en psql).
--
-- Ejecución:
--   python seed.py
--   psql -U postgres -d libreria -f test/solo_agregado.sql

\echo '=== Estado inicial de movimiento_stock ==='
SELECT id, libro_id, venta_id, usuario_id, cantidad, motivo
FROM movimiento_stock
ORDER BY id;

\echo '=== Intento 1: UPDATE sobre movimiento_stock (debe ser RECHAZADO por el disparador) ==='
UPDATE movimiento_stock
SET cantidad = 999
WHERE id = 1;

\echo '=== Intento 2: DELETE sobre movimiento_stock (debe ser RECHAZADO por el disparador) ==='
DELETE FROM movimiento_stock
WHERE id = 1;

\echo '=== Verificación posterior: las filas siguen intactas ==='
SELECT id, libro_id, venta_id, usuario_id, cantidad, motivo
FROM movimiento_stock
ORDER BY id;
