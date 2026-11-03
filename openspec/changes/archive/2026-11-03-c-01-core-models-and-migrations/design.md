# Design: C-01 Core, Models, and Migrations

## Context

El proyecto parte del Trabajo Práctico de los capítulos 1 a 4 (catálogo, clientes y ventas) y debe dividirse en dos entregables independientes según la página 24 del enunciado:
1. `despliegue/`: copia intacta del TP de los capítulos 1 a 4 que será contenedorizada con `python:3.12-alpine`.
2. `parcial/`: evolución del sistema a los capítulos 5 y 6, incorporando autenticación, autorización en base de datos, arquitectura en capas (`Router → Service → UoW → Repository → Model`), borrado lógico en libros, movimientos de stock de sólo agregado y evolución del esquema mediante las migraciones 3 y 4 de Alembic.

## Goals / Non-Goals

**Goals:**
- Estructurar `parcial/` y `despliegue/` en la raíz del repositorio cumpliendo la organización obligatoria de archivos (`parcial/main.py`, `parcial/seed.py`, `parcial/app/core/*`).
- Implementar `Settings` con `pydantic-settings` y `@computed_field` sin ningún secreto ni contraseña por defecto en el código.
- Garantizar que toda petición autenticada comparta una única `AsyncSession` (`SessionDep`) entre las dependencias de autorización y el `UnitOfWork` del módulo.
- Declarar todas las relaciones de SQLModel con `lazy="raise"` para impedir consultas `N+1` accidentales por carga perezosa.
- Incorporar las migraciones 3 (`9a4e7c2b1d80`, autogenerada y revisada) y 4 (`c8e31f5a9021`, manual con el disparador PL/pgSQL `trg_movimiento_stock_solo_agregado`) completamente reversibles.

**Non-Goals:**
- Implementar los endpoints de negocio de `/auth`, `/usuarios`, `/eventos`, catálogo con stock o ventas (pertenecen a `C-02`, `C-03` y `C-04`).
- Escribir el `Dockerfile` de `despliegue/` (pertenece a `C-05`).

## Decisions

1. **Unificación de `AsyncSession` entre Auth y `UnitOfWork`**:
   - *Decisión*: `UnitOfWork.__init__(session: AsyncSession)` recibe la sesión inyectada por `SessionDep` (`Depends(get_session)`), que es la misma instancia cacheada por FastAPI para `get_usuario_actual` y `requiere_rol`. `UnitOfWork.__aexit__` ejecuta `commit()` o `rollback()` pero nunca `close()`.
   - *Racional*: Evita tomar dos conexiones del pool por petición autenticada y permite que el servicio o el router lean atributos tras el `commit()` (con `expire_on_commit=False`).

2. **Índices únicos parciales con `postgresql_where`**:
   - *Decisión*: Definir `Index("uq_asignacion_rol_usuario_rol_abierta", "usuario_id", "rol", unique=True, postgresql_where=text("revocada_en IS NULL"))` en `AsignacionRol` e `Index("uq_libro_isbn_vigente", "isbn", unique=True, postgresql_where=text("borrado_en IS NULL"))` en `Libro`.
   - *Racional*: Delega en PostgreSQL la invariante de unicidad únicamente sobre las filas vigentes (`RN-01`, `RN-03`, `RN-13`), permitiendo conservar el historial de roles revocados y libros dados de baja sin bloquear futuras altas.

3. **Trigger `FOR EACH ROW BEFORE UPDATE OR DELETE` en la 4ª migración**:
   - *Decisión*: Crear la función `impedir_modificacion_movimiento_stock()` que lanza `RAISE EXCEPTION` con `ERRCODE = '23514'` y `CONSTRAINT = 'ck_movimiento_stock_solo_agregado'` ante cualquier `UPDATE` o `DELETE` en `movimiento_stock`.
   - *Racional*: Garantiza el sólo agregado (`RN-12`) incluso desde `psql` (`test/solo_agregado.sql`, Caso `C-14`), mientras permite `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` cuando `seed.py` reinicia los datos de prueba.

## Risks / Trade-offs

- **Compatibilidad de arranque (`uvicorn main:app` vs `uvicorn app.main:app`)**: La tabla de estructura obligatoria (pág. 8) pide `main.py` en la raíz de `parcial/`. Para evitar fallos si se invoca con `app.main:app`, `parcial/app/main.py` reexporta `app` y `lifespan` desde `parcial/main.py`.
