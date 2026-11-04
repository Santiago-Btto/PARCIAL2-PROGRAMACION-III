# Proposal

## Why

Después de C-03, clientes y ventas siguen recibiendo `AsyncSession` en los servicios, confirman por su cuenta, listan con `limit/offset` y están montados en el grupo abierto. El registro de una venta escribe `Libro.stock` directamente sin dejar movimientos, y `seed.py` hace lo mismo, así que RN-11 todavía no vale para todo el sistema. Tampoco existen `/mis-ventas` ni el control de dueño del detalle de una venta, y el seed, el README y los casos `.http` son los del TP de los capítulos 1 a 4.

## What Changes

- Refactorizar `clientes` y `ventas` a `Router → Service → UoW → Repository → Model`, con `ClienteRepository`, `PerfilClienteRepository`, `VentaRepository`, `ClientesUnitOfWork` y `VentasUnitOfWork`.
- **BREAKING**: montar clientes y ventas en el grupo protegido; clientes y el registro y listado de ventas exigen `VENDEDOR` o `ADMIN`.
- **BREAKING**: reemplazar `limit/offset` de clientes y ventas por `Pagina[T]` con `page/size`.
- Registrar la venta en un solo Unit of Work: validar cliente, bloquear y validar libros (existencia, vigencia y stock) antes de escribir, copiar precios, calcular el total y descontar cada renglón por `cambiar_stock`, con un movimiento negativo por renglón.
- Agendar el aviso del comprobante sólo cuando la venta se confirmó, en un logger visible con el arranque normal de uvicorn.
- Agregar `GET /mis-ventas` y el control personal/dueño de `GET /ventas/{id}` sin `requiere_rol`.
- Reescribir `seed.py` con los datos de la consigna, cargando el stock por el punto único y la venta 1 con el mismo service de `POST /ventas`.
- Reemplazar los `.http` del TP por la suite C-01 a C-16, el script de evidencia C-15 y el README del parcial.

## Capabilities

### New Capabilities

- `clientes-y-ventas`: clientes protegidos y paginados, registro transaccional de ventas con stock trazable, lo propio, lecturas sin N+1, aviso en segundo plano y estado inicial de la base.

### Modified Capabilities

Ninguna en sus requisitos. Se consumen `stock-y-baja-logica` (contrato `cambiar_stock`), `auth-usuarios-and-rbac` y `catalogo` sin cambiar sus contratos.

## Impact

Código: `parcial/app/modules/clientes/`, `parcial/app/modules/ventas/`, `parcial/main.py`, `parcial/seed.py`, `parcial/README.md`, `parcial/test/` y `parcial/scripts/`. Ajustes mínimos fuera de esos módulos: `UsuariosUnitOfWork` usa `ClienteRepository` en lugar de un `BaseRepository` genérico, y los listados de libros convierten cada item a su contrato leyendo por atributos (`convertir_pagina`) para que editorial y género lleguen a la respuesta.

Sin migraciones ni dependencias nuevas. `despliegue/` queda fuera (C-05).
