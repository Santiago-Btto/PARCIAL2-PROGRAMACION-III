# Proposal

## Why

El parcial de Programación III (Unidades 1 a 6) exige partir del Trabajo Práctico de los capítulos 1 a 4 y separar el repositorio en dos proyectos independientes (`parcial/` y `despliegue/`), incorporando en `parcial/` configuración tipada sin secretos por defecto (`pydantic-settings`), arquitectura en capas con `Repository` y `UnitOfWork`, modelos de acceso (`Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`), borrado lógico en `Libro`, trazabilidad de stock (`MovimientoStock`) y las migraciones 3 (autogenerada) y 4 (manual con disparador de sólo agregado) de Alembic. Este change (`C-01`) establece toda la infraestructura transversal y el esquema de base de datos de los que dependen los restantes bloques del parcial.

## What Changes

- **Separación de directorios raíz**: creación de `parcial/` (proyecto evolucionado a capítulos 1 a 6 con `main.py` y `seed.py` en su raíz) y `despliegue/` (copia congelada del TP capítulos 1 a 4 para Docker y VPS).
- **BREAKING — Configuración con `pydantic-settings` (`parcial/app/core/config.py`)**: reemplazo de `DATABASE_URL` directo por variables individuales `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` y `@computed_field` para `database_url`, sumando `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `COOKIE_SECURE`, `BCRYPT_ROUNDS` y `BCRYPT_MAX_CONCURRENT` sin valores por defecto para secretos.
- **Ciclo de vida y salud (`parcial/app/core/database.py`, `parcial/main.py`, `parcial/app/modules/health/router.py`)**: inicialización en `lifespan` del motor asincrónico, fábrica de sesiones (`expire_on_commit=False`), semáforo de `bcrypt` y hash ficticio (`dummy_password_hash`), cierre con `dispose()` al apagar, y endpoints `GET /health/live` (`200`) y `GET /health/ready` (`200` / `503`).
- **Patrones base de persistencia y paginación (`parcial/app/core/repository.py`, `unit_of_work.py`, `paginacion.py`, `errores.py`)**: implementación de `BaseRepository[T]` y `SoftDeleteRepository[T]` (`flush()` sin `commit()`), `UnitOfWork` asincrónico (comparte `SessionDep`, hace `commit()` o `rollback()` sin cerrar la sesión) y envoltorio `Pagina[T]` (`{items, total, page, size, pages}` con `422` cuando `page > pages`).
- **Primitivas de seguridad y dependencias (`parcial/app/core/security.py`, `dependencies.py`)**: hashing y verificación `bcrypt` fuera del bucle de eventos (`asyncio.to_thread` + `asyncio.Semaphore`), límite de 72 bytes en UTF-8, emisión/verificación de JWT en cookie `HttpOnly` (`access_token`), y dependencias `get_usuario_actual` (`401`), `verificar_cambio_password_resuelto` (`403`) y `requiere_rol` (`403` consultando `asignacion_rol` en cada petición).
- **Modelos de dominio y Migraciones 3 y 4 (`parcial/app/modules/*/models.py`, `parcial/migrations/versions/`)**:
  - Nuevas tablas `usuario`, `asignacion_rol` (con índice único parcial `uq_asignacion_rol_usuario_rol_abierta` `WHERE revocada_en IS NULL`), `intento_acceso`, `evento_seguridad` y `movimiento_stock` (`CHECK cantidad <> 0`).
  - Modificación de `cliente` (`usuario_id` nullable UNIQUE `ON DELETE SET NULL`) y `libro` (`borrado_en` timestamptz e índice único parcial `uq_libro_isbn_vigente` `WHERE borrado_en IS NULL`).
  - Tercera migración (`9a4e7c2b1d80`) generada con `--autogenerate` y revisada, y cuarta migración (`c8e31f5a9021`) escrita a mano con la función y el disparador PL/pgSQL `trg_movimiento_stock_solo_agregado` (`BEFORE UPDATE OR DELETE ON movimiento_stock`) más `parcial/test/solo_agregado.sql`.

## Capabilities

### New Capabilities
- `core-lifecycle-and-architecture`: Configuración con `pydantic-settings` sin secretos por defecto, `lifespan` con pool y hash ficticio, endpoints de salud, `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork`, paginación `Pagina[T]` y primitivas `security.py` / `dependencies.py`.
- `domain-schema-and-migrations`: Modelos SQLModel de acceso, catálogo con borrado lógico y movimientos de stock, índices únicos parciales y migraciones 3 y 4 de Alembic (incluyendo el disparador append-only sobre `movimiento_stock`).

### Modified Capabilities
<!-- No existing capabilities in openspec/specs/ yet -->

## Impact

- **Código afectado**: `despliegue/` (copia completa del TP Cap. 1 a 4), `parcial/main.py`, `parcial/app/core/*`, `parcial/app/modules/usuarios/models.py`, `parcial/app/modules/clientes/models.py`, `parcial/app/modules/libros/models.py`, `parcial/app/modules/ventas/models.py`, `parcial/app/modules/health/router.py`, `parcial/migrations/versions/9a4e7c2b1d80_*.py`, `parcial/migrations/versions/c8e31f5a9021_*.py` y `parcial/test/solo_agregado.sql`.
- **Dependencias (`parcial/requirements.txt`)**: se agregan `pydantic-settings>=2.0`, `bcrypt>=4.0` y `PyJWT>=2.8`.
