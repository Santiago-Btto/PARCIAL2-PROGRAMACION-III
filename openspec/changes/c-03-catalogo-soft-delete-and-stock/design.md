# Design

## Context

Ver `proposal.md` para motivación y límites. Base revisada: `e878f26`, C-01 y C-02 archivados. Los cuatro módulos de catálogo todavía reciben `AsyncSession` en servicios y confirman directamente. Las colecciones usan `limit/offset`; libro permite `stock` en alta y PATCH y no filtra `borrado_en`. El esquema, el índice parcial de ISBN y el disparador de movimientos ya existen.

El modelo real declara `Libro.autorias`, no `autores_asociados` como indica una línea del roadmap. `libros/service.py` contiene precarga y `_escapar_like` reutilizables, pero traduce el antiguo `uq_libro_isbn` en vez de `uq_libro_isbn_vigente`. `generos/router.py` ofrece POST y dos GET, sin PATCH.

Baseline exploratorio ejecutado por el agente de exploración con `F:\TPS\parcial-programacion\.venv\Scripts\python.exe`, un entorno prestado (Python 3.13.5, FastAPI 0.162, SQLModel 0.0.48, pytest 9.2): `pytest test -q -p no:cacheprovider`, desde `parcial/`, dio **31 passed y 1 failed**. El fallo previo está en `test/test_usuarios_router.py:183`, `test_main_montaje_grupos_abierto_y_protegido`: `AttributeError: '_IncludedRouter' object has no attribute 'path'`. Esto no valida un entorno reproducible del repo ni autoriza corregir C-02. No hay pruebas automatizadas de catálogo ni runner declarado en `requirements.txt`. `test/conftest.py` sustituye globalmente `asyncio.to_thread`; esos tests no prueban ejecución real fuera del event loop.

Las skills de dominio exigidas por AGENTS no se encontraron en el repo ni ubicaciones activas consultadas. Antes de aplicar se deberá resolver su disponibilidad o acordar explícitamente una alternativa; no instalarlas globalmente sin necesidad.

## Goals / Non-Goals

**Goals:** aplicar los contratos de ambas specs mediante capas ya establecidas; centralizar consultas de libros y variaciones de stock; permitir integración posterior sin nueva transacción ni otra lógica de inventario.

**Non-Goals:** modificar autenticación, usuarios, clientes, ventas, seed, despliegue, dependencias de ejecución o migraciones. No certificar RN-11 global, bloqueo de ventas sobre bajas, historial de ventas ni evidencias completas C-01 a C-16; esos puntos necesitan C-04. No añadir endpoints por generalizar la descripción del roadmap.

## Decisions

### 1. Composición por módulo y límites de sesión

Crear `repository.py` y `unit_of_work.py` en cada módulo. Editoriales, géneros y autores heredan `BaseRepository`; `LibroRepository` hereda `SoftDeleteRepository`; `MovimientoStockRepository` hereda `BaseRepository`, sin exponer operaciones de modificación desde la API.

Las dependencias de router construyen el UoW con `SessionDep` y lo pasan sin abrir. El servicio abre `async with uow:`; repositorios sólo agregan/consultan/precargan y hacen `flush()`. Nadie cierra la sesión compartida. Los UoW de entidades que consultan sus libros componen `LibroRepository` en la misma sesión para reutilizar filtros y precarga, evitando imports servicio-a-servicio.

El `UnitOfWork` base actual no revierte automáticamente si falla su propio `commit()`. Los servicios que traduzcan `IntegrityError` deberán hacerlo alrededor de todo el bloque y asegurar `rollback()` antes de propagar el conflicto, incluidos errores al salir. No ampliar este change con una reescritura transversal de UoW.

Alternativa descartada: repositorio genérico configurable para todos los módulos o servicios que construyan UoW; agrega abstracción y contradice la arquitectura vigente.

### 2. Reutilización del repositorio base con regresión real

`core/repository.py` importa `sqlalchemy.select` y pasa sus resultados a `AsyncSession.exec()` como si fueran entidades. Hay una sospecha de resultados `Row` en vez de modelos que los mocks existentes podrían ocultar. Antes de usarlo, reproducir `get_by_id`, `get_all` y variantes soft-delete con sesión real y esquema migrado. Si se confirma, reportar el defecto previo y obtener revisión de la corrección mínima (por ejemplo, selección escalar compatible con SQLModel), con RED/GREEN y regresión C-02. No adaptar nuevos repositorios a resultados incorrectos ni tocar `usuarios/repository.py` automáticamente.

Alternativa descartada: duplicar CRUD o cubrir sólo con mocks; impediría verificar la base que C-03 debe reutilizar. El contrato de la spec core no cambia.

### 3. Paginación y consultas de catálogo

Reutilizar `PageQuery`, `SizeQuery`, `calcular_paginas` y `Pagina`. Cada listado cuenta y obtiene items con las mismas condiciones, orden por ID y offset interno `(page-1)*size`; se elimina el contrato HTTP `limit/offset`, no el mecanismo SQL interno de paginación. También se paginan libros por editorial, género y autor, y movimientos. Verificar existencia de la entidad padre para devolver `404`; si existe sin libros, devolver página vacía.

Mover la consulta de libros y el escape literal de LIKE al repositorio, conservando parámetros ligados, `ilike`, combinación con género y filtro vigente tanto en count como items. Para detalle precargar `joinedload(Libro.editorial)`, `joinedload(Libro.genero)` y `selectinload(Libro.autorias).joinedload(LibroAutor.autor)`. El listado conserva su DTO actual; el listado por autor conserva rol y orden. La precarga pertenece al método que consume cada respuesta, manteniendo `lazy="raise"`.

Alternativa descartada: filtrar libros borrados en Python después de paginar; corrompe total, páginas y cantidad de items.

### 4. Contratos compatibles excepto cambios solicitados

Agregar `ConfigDict(extra="forbid")` a cada entrada, incluidas autorías. Alta libro recibe `stock_inicial=0`, con límites actuales de stock. PATCH elimina `stock`; `stock_inicial` tampoco existe en ese DTO. Conservar ISBN, título, precio, editorial y género del PATCH actual, las validaciones heredadas y el null explícito sólo en género. Los ejemplos de título/precio de la consigna no se interpretan como instrucción de eliminar campos existentes.

No crear PATCH de géneros: no existe en API ni tabla de consigna. Conservar las rutas actuales y dividir routers públicos/protegidos por módulo, usando la dependencia `requiere_rol("ADMIN")` actual y el único control de cambio obligatorio ya montado en `main.py`. Integración en main limitada al catálogo; clientes y ventas siguen pendientes de C-04.

Alternativa descartada: endurecer permisos dentro de los servicios o modificar autenticación; duplicaría políticas ya implementadas en C-02.

### 5. Punto de cambio de stock sin commit propio

Crear una función compartida en `libros/stock.py`, con contrato orientativo:

```python
async def cambiar_stock(
    uow, *, libro_id: int, cantidad: int,
    usuario_id: int, motivo: str, venta_id: int | None = None,
): ...
```

Recibe un UoW ya abierto que expone repositorios `libros` y `movimientos`; no crea sesión, no abre otra transacción y no confirma. Obtiene el libro con bloqueo de fila, refrescando estado si ya estaba en el identity map, verifica vigencia y stock resultante entre cero y `MAX_ID`, y realiza la única asignación al stock de catálogo junto a `MovimientoStock`. Un resultado fuera de esos límites genera `409` antes de escribir; entradas HTTP fuera de límites generan `422`. El repositorio realiza consultas/bloqueos y flush; la regla de variación permanece en la función. La inicialización estructural del modelo en stock cero no es una variación de inventario.

Alta crea libro/autorías con stock cero y sólo invoca el punto si `stock_inicial > 0`. Reposición normaliza y valida el motivo (no sólo espacios; máximo 200), usa el actor de la sesión y `venta_id=None`. La función acepta negativos y `venta_id` para que C-04 la invoque dentro de `VentasUnitOfWork`; esas ramas se prueban mediante el contrato sin implementar `/ventas`.

Reposición y baja deben adquirir el mismo bloqueo de libro para que la comprobación de vigencia y la escritura no compitan entre sí. Para ventas futuras con varios libros, C-04 deberá ordenar bloqueos por ID. La concurrencia con el escritor legado de ventas no queda resuelta hasta esa integración.

Alternativa descartada: leer-modificar-escribir sin bloqueo, recalcular stock desde el total en cada alta o confirmar el movimiento en otra sesión; permitirían pérdidas o romperían atomicidad.

### 6. Baja, historial y errores

Baja llama `soft_delete` bajo UoW y bloqueo, no `delete`; retorna `204` sin cuerpo. Lecturas habituales y asociaciones excluyen bajas. Histórico de movimientos usa lookup explícito incluyendo bajas y filtra siempre por `libro_id`, nunca por ISBN. Reposición distingue inexistente (`404`) de baja (`409`); baja repetida devuelve `404`.

Traducir el índice real `uq_libro_isbn_vigente` y restricciones existentes con el traductor y mensajes propios. Unicidad queda a cargo de PostgreSQL; no agregar SELECT de comprobación previa. No actualizar ni eliminar movimientos. Las migraciones existentes bastan; no agregar filtros globales ORM que oculten libros en ventas históricas.

## Risks / Trade-offs

- [Stock legado y seed sin movimientos] → documentar handoff a C-04 y verificar la igualdad stock/suma sobre datos creados por C-03; no usarlo para afirmar invariante global ni inventar backfill.
- [Fallo previo en baseline prestado] → preparar entorno aislado del repo con dependencias declaradas, reproducir y registrar baseline. Si persiste un fallo previo, detener apply y reportar; su corrección requiere un alcance separado.
- [Mocks ocultan semántica ORM] → pruebas reales de selección, restricciones, rollback, locking y ISBN en PostgreSQL 16 aislado, creado por Alembic; nunca `metadata.create_all`.
- [Suite global altera asyncio] → aislar pruebas de concurrencia DB y no presentar la suite existente como prueba de asincronía/bcrypt.
- [Cambio de contrato listas/stock] → probar nuevos ejemplos de catálogo y comunicar al responsable de C-04 los payloads, paginación y helper antes de integrar.
- [Regresión de main compartido con C-02/C-04] → revisar diff sólo de montaje de catálogo y ejecutar regresión de rutas/auth; no arreglar su comportamiento fuera de este alcance.

## Migration Plan

1. Revisar y aprobar esta propuesta de gobernanza ALTA. Resolver skills y baseline antes de producción.
2. Implementar por módulo con TDD estricto y tests de PostgreSQL aislado, guardando evidencia real de RED/GREEN/triangulación/refactor.
3. Usar fixtures de prueba compatibles con migraciones; no ejecutar el seed legado para acreditar RN-11 y no cambiar datos personales/producción.
4. Verificar contratos de catálogo, regresión existente, SQL de relaciones, rollback y reposiciones concurrentes. Comunicar handoff C-04.
5. Commit local de C-03 tras validar; no push ni archive automático. El archivo de esta propuesta sigue abierto hasta que el usuario pida cierre.

No hay migración de esquema nueva. Un rollback de código podría reintroducir escrituras sin movimientos y no revierte bajas o movimientos ya registrados; coordinarlo con los responsables de ventas y preservar el historial, sin borrado ni ajuste silencioso de datos.
