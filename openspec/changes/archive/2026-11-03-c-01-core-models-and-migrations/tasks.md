# Tasks

## 1. Estructura de Proyectos y Configuración (`Ejercicio 1`)

- [x] 1.1 Separar el repositorio en `parcial/` (con `main.py` y `seed.py` en su raíz) y `despliegue/` (copia intacta del TP Capítulos 1 a 4), verificando que ambas carpetas existan con todos sus archivos base.
- [x] 1.2 Actualizar `parcial/requirements.txt` y `parcial/env.example` incorporando `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8` y las variables `POSTGRES_*`, `JWT_*` y `BCRYPT_*` sin secretos reales.
- [x] 1.3 Implementar `Settings` en `parcial/app/core/config.py` con `pydantic-settings`, validación sin valores por defecto para `POSTGRES_PASSWORD` ni `JWT_SECRET_KEY`, y `@computed_field` para `database_url`.
- [x] 1.4 Actualizar `parcial/app/core/database.py`, `parcial/main.py` y `parcial/app/modules/health/router.py` con el pool configurado en `lifespan`, `dummy_password_hash`, `dispose()` al apagar y los endpoints `/health/live` y `/health/ready`.

## 2. Capas Base: Repositorios, Unit of Work, Paginación y Seguridad (`Ejercicios 3, 4, 5 y 6`)

- [x] 2.1 Implementar `BaseRepository[T]` y `SoftDeleteRepository[T]` en `parcial/app/core/repository.py` garantizando que las escrituras hagan `flush()` y nunca `commit()`.
- [x] 2.2 Implementar `UnitOfWork` base en `parcial/app/core/unit_of_work.py` que confirme al salir del bloque `async with`, revierta ante excepción y no cierre la sesión compartida.
- [x] 2.3 Implementar `Pagina[T]`, `calcular_paginas` y `armar_pagina` en `parcial/app/core/paginacion.py` junto con las excepciones de dominio en `parcial/app/core/errores.py`.
- [x] 2.4 Implementar `parcial/app/core/security.py` (`bcrypt` con `asyncio.to_thread` + `asyncio.Semaphore`, límite de 72 bytes y JWT en cookie `HttpOnly` `access_token`) y `parcial/app/core/dependencies.py` (`get_usuario_actual`, `verificar_cambio_password_resuelto` y `requiere_rol`).

## 3. Modelos de Dominio y Migraciones 3 y 4 (`Ejercicios 2 y 7`)

- [x] 3.1 Crear `parcial/app/modules/usuarios/models.py` (`Usuario`, `AsignacionRol` con índice parcial `uq_asignacion_rol_usuario_rol_abierta`, `IntentoAcceso`, `EventoSeguridad`) y actualizar `Cliente`, `Libro` (`borrado_en`, `uq_libro_isbn_vigente` y `MovimientoStock`), `Venta` y `parcial/app/core/modelos.py`.
- [x] 3.2 Incorporar la 3ª migración de Alembic (`9a4e7c2b1d80_acceso_roles_borrado_logico_y_movimiento_stock.py`) con su encabezado de revisión y `downgrade()` reversible.
- [x] 3.3 Escribir a mano la 4ª migración de Alembic (`c8e31f5a9021_disparador_solo_agregado_movimiento_stock.py`) con el disparador `trg_movimiento_stock_solo_agregado` y el script de prueba `parcial/test/solo_agregado.sql`, verificando que todos los módulos compilen sin errores con `python -m compileall`.
