# Design

## Context

Base: `ea9db1c` (C-01, C-02 y C-03 archivados). `cambiar_stock` y su handoff (`parcial/test/C03_C04_HANDOFF.md`) definen el contrato de stock: el llamador abre el UoW, ofrece `libros.get_for_update`, `libros.update` y `movimientos.add` sobre una sesión, y confirma o revierte. `ventas/service.py` y `seed.py` todavía escriben `Libro.stock` directamente.

## Goals / Non-Goals

**Goals:** cerrar RN-09, RN-10, RN-11 y RN-14 en todo el sistema; dejar clientes y ventas con las mismas capas que el resto; dejar el estado inicial y la suite de casos de la consigna.

**Non-Goals:** concurrencia más allá del bloqueo por fila que ya hace `get_for_update` (capítulo 7), colas de tareas (capítulo 8), cambios de esquema y el despliegue de `despliegue/`.

## Decisions

### 1. Un Unit of Work por módulo, sin servicios que llamen a otros servicios

`VentasUnitOfWork` compone `ventas`, `clientes`, `libros` y `movimientos` sobre la sesión de la petición; los nombres `libros` y `movimientos` son los que pide `cambiar_stock`. `ClientesUnitOfWork` compone `clientes`, `perfiles` y `ventas` para `GET /clientes/{id}/ventas`. Los repositorios sólo importan modelos, así que no hay ciclos entre módulos.

### 2. Validar todo antes de la primera escritura

El service recorre los renglones ordenados por `libro_id`, bloquea cada libro con `get_for_update` y responde 409 si no existe, está dado de baja o no alcanza. Recién después agrega la venta (flush para obtener su id) y descuenta cada renglón con `cambiar_stock(..., venta_id=...)`. El orden estable evita interbloqueos cruzados entre dos ventas. Como la validación es previa, un rechazo no consume la secuencia de `venta` y los ids de los casos de prueba son predecibles. Si igual fallara una escritura, la excepción sale del bloque y el UoW revierte todo; un `IntegrityError` se traduce por nombre de restricción.

Alternativa descartada: descontar y dejar que el CHECK `stock >= 0` rechace. Funciona, pero responde con un mensaje genérico y no dice qué libro no alcanzó.

### 3. Detalle de venta con dueño o personal

`GET /ventas/{id}` no lleva `requiere_rol`. El router entrega al service el usuario y sus roles vigentes (dependencia `get_roles_vigentes`, misma sesión). El service lee el detalle (404 si no existe), devuelve si hay rol `VENDEDOR`/`ADMIN` vigente o si `venta.cliente.usuario_id` es el usuario, y si no responde 403. El cliente ya viene precargado con la venta: la comprobación no agrega consultas y C-15 se mantiene en un número fijo.

### 4. Lecturas y conversión a contratos

`VentaRepository.obtener_detalle` usa `joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`, sin filtro de vigencia: un libro dado de baja sigue apareciendo en ventas viejas. Los listados devuelven `Pagina` de modelos de tabla; los routers convierten cada item con `model_validate(..., from_attributes=True)` (`convertir_pagina`). Sin esa conversión, la serialización por defecto de un modelo de tabla dentro de un `BaseModel` común lo vuelca sin relaciones; se aplicó también a los listados de libros de C-03, que tenían el mismo riesgo con editorial y género.

### 5. Aviso en segundo plano

El router agenda `avisar_comprobante` después de que `service.crear` devolvió: si la venta se revirtió, el service lanzó y la tarea nunca se agenda. El logger es `uvicorn.error.ventas`: propaga al handler que uvicorn configura en su arranque normal, sin depender de `basicConfig`.

### 6. Seed por los mismos caminos que la API

Hash bcrypt antes de abrir la transacción, `TRUNCATE ... RESTART IDENTITY CASCADE` (no dispara el trigger, que es por fila sobre UPDATE/DELETE), alta de catálogo con `stock=0` y un `cambiar_stock` de «Stock inicial» por libro (actor: admin), y la venta 1 con `ventas.service.crear` (actor: vendedor). Resultado: stock igual a la suma de movimientos en los cinco libros, sin escrituras directas de stock en ningún lugar del código.

## Risks / Trade-offs

- La conversión explícita a contratos agrega una línea por endpoint de listado; a cambio no depende de cómo FastAPI serializa modelos anidados.
- `/mis-ventas` resuelve la ficha por `cliente.usuario_id` (UNIQUE): una consulta extra frente a guardar el cliente en el token, pero respeta que los permisos se decidan en la base.
