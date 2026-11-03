# Visión y Objetivos

## Propósito del sistema
Evolucionar el sistema backend asincrónico de la Librería (capítulos 1 a 4: catálogo, clientes y ventas) hasta el capítulo 6 incorporando control de acceso con usuarios y roles vigentes en base de datos, capa de repositorios y Unit of Work transaccional, trazabilidad de stock de sólo agregado (`movimiento_stock`), borrado lógico de libros y el empaquetado/despliegue en contenedor Docker (`python:3.12-alpine`) sobre el VPS de la cátedra.

El sistema abre la librería tanto a su personal interno (administradores y vendedores) como a sus clientes web, garantizando que cada operación de negocio de múltiples escrituras sea atómica y que la base de datos imponga las invariantes de integridad (unicidad parcial en registros vigentes, claves foráneas, `CHECK` constraints y disparador de sólo agregado).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **Visitante (Público)** | Explorar el catálogo de libros vigente y registrarse como cliente web | Consultar libros por título/género, ver libros por editorial/género/autor, iniciar sesión |
| **Cliente (`CLIENTE`)** | Consultar sus propias compras realizadas en la librería | Autoregistrarse en la web (creando usuario, rol y ficha de cliente en un solo paso), ver el detalle de sus ventas (`/mis-ventas` y `/ventas/{id}` propias), cambiar su contraseña |
| **Vendedor (`VENDEDOR`)** | Registrar ventas de mostrador y administrar fichas de clientes | Dar de alta clientes y perfiles, actualizar datos de clientes, consultar listado e historial de ventas de cualquier cliente |
| **Administrador (`ADMIN`)** | Mantener el catálogo completo, gestionar el stock y administrar el personal y sus roles | Alta/edición/baja lógica de libros, reposición y auditoría de movimientos de stock, alta/edición de editoriales/géneros/autores, alta de personal con contraseña provisoria, asignación y revocación de roles con vigencia, auditoría de `evento_seguridad` |

## Alcance v2.0 (Parcial Capítulos 1 a 6)
- **Carpeta `parcial/` (Ejercicios 1 a 8):**
  - Reorganización en capas estrictas: `Router → Service → UoW → Repository → Model`.
  - Configuración tipada con `pydantic-settings` (`Settings`) sin secretos ni contraseñas por defecto, `@computed_field` para `database_url`, y ciclo de vida (`lifespan`) que administra motor, pool, fábrica de sesiones y hash ficticio.
  - Evolución del esquema exclusivamente con **Alembic** (4 migraciones: 2 del TP + 3ª autogenerada con tablas de acceso/stock/cambios + 4ª escrita a mano con trigger PL/pgSQL append-only sobre `movimiento_stock`).
  - Autenticación con `bcrypt` fuera del event loop (`asyncio.to_thread` + `asyncio.Semaphore`), límite de 72 bytes, protección contra enumeración de cuentas (mismo mensaje y tiempo constante con hash ficticio), rate-limiting de login (`429 Retry-After` tras 5 fallos en 60s registrados en sesión independiente sobre `intento_acceso`) y JWT en cookie `HttpOnly` (`access_token`).
  - Autorización consultando roles vigentes en `asignacion_rol` en cada petición (`401` vs `403`), autoprotección de `ADMIN`, y dos grupos de rutas en `main.py` para exigir el cambio de contraseña provisoria (`debe_cambiar_password`).
  - Borrado lógico de libros (`borrado_en`) con índice único parcial de ISBN (`WHERE borrado_en IS NULL`) y control de stock exclusivamente mediante movimientos (`Stock inicial`, reposición y venta).
  - Paginación estandarizada `{items, total, page, size, pages}` con error `422` al pedir páginas inexistentes.
  - Lecturas sin N+1 (`lazy="raise"` + precarga en repositorios) y notificación simulada de comprobante de venta con `BackgroundTasks`.
- **Carpeta `despliegue/` (Ejercicios 9 y 10):**
  - Empaquetado del TP original (capítulos 1 a 4) en una imagen Docker basada en `python:3.12-alpine` (< 100 MB), usuario sin privilegios, `HEALTHCHECK` sobre `/health/ready`, migraciones al arrancar y despliegue en línea en el VPS conectado al PostgreSQL del servidor.

## Fuera de alcance
- **Control de concurrencia pesimista/optimista sobre stock (Capítulo 7):** Dos ventas simultáneas del último ejemplar pueden producir una actualización perdida si ambas leen `stock = 1` antes de escribir (aunque el `CHECK stock >= 0` impide stock negativo).
- **Colas de tareas distribuidas con Redis / Celery (Capítulo 8):** El aviso al cliente al registrar una venta se ejecuta en el mismo proceso con `BackgroundTasks`.
- **Segundo rol de base de datos para `movimiento_stock`:** El sólo agregado se garantiza con el disparador de la 4ª migración; la aplicación se conecta con un único rol de PostgreSQL.

## Métricas de éxito
1. `alembic upgrade head`, `alembic downgrade base` y nuevamente `alembic upgrade head` ejecutan sin errores sobre una base vacía.
2. `python seed.py` deja el estado inicial exacto requerido por la cátedra, cumpliendo que para los 5 libros `libro.stock == SUM(movimiento_stock.cantidad)`.
3. Los 16 casos de prueba funcionales y de seguridad (`C-01` a `C-16`, incluyendo `test/solo_agregado.sql`) y los 8 casos de despliegue (`D-01` a `D-08`) pasan con los códigos HTTP y salidas esperadas.
4. Ninguna credencial ni secreto figura en el código, en `alembic.ini`, en el historial de Git ni en las capas de la imagen Docker.
